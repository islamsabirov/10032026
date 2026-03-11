"""
Async MongoDB database manager with connection pooling and indexes.
Compatible with motor 3.3.2 and pymongo 4.8.0+
"""

import asyncio
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timedelta
from bson import ObjectId
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorDatabase,
    AsyncIOMotorCollection
)

from config import config
from utils.logger import logger


class Database:
    """
    MongoDB database manager with connection pooling and automatic reconnection
    """
    
    _instance: Optional['Database'] = None
    _client: Optional[AsyncIOMotorClient] = None
    _db: Optional[AsyncIOMotorDatabase] = None
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def connect(self):
        """Establish database connection and create indexes"""
        try:
            # Log connection attempt
            logger.info("🔄 Connecting to MongoDB...")
            
            # Create MongoDB client with connection pooling
            self._client = AsyncIOMotorClient(
                config.MONGODB_URI,
                maxPoolSize=50,
                minPoolSize=10,
                maxIdleTimeMS=30000,
                connectTimeoutMS=5000,
                serverSelectionTimeoutMS=5000,
                retryWrites=True,
                retryReads=True
            )
            
            # Test connection with ping
            await self._client.admin.command('ping')
            
            # Get database
            self._db = self._client[config.MONGODB_DB_NAME]
            
            # Create indexes (with error handling)
            try:
                await self._create_indexes()
            except Exception as e:
                logger.warning(f"⚠️ Index creation warning (non-critical): {e}")
            
            logger.info("✅ MongoDB connected successfully")
            
            # Log database stats
            await self._log_stats()
            
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            raise
    
    async def _log_stats(self):
        """Log database statistics"""
        try:
            # Get collection stats
            collections = await self._db.list_collection_names()
            logger.info(f"📊 Available collections: {', '.join(collections) if collections else 'none'}")
            
            # Count documents in each collection
            if 'users' in collections:
                users_count = await self._db.users.count_documents({})
                logger.info(f"👥 Users in database: {users_count}")
            
            if 'movies' in collections:
                movies_count = await self._db.movies.count_documents({})
                logger.info(f"🎬 Movies in database: {movies_count}")
                
        except Exception as e:
            logger.debug(f"Stats logging failed: {e}")
    
    async def _create_indexes(self):
        """Create all database indexes for performance"""
        
        # Ensure collections exist
        collections = await self._db.list_collection_names()
        
        # Users collection indexes
        if 'users' not in collections:
            await self._db.create_collection('users')
        
        users = self._db.users
        try:
            await users.create_index("user_id", unique=True)
            await users.create_index("username", sparse=True)
            await users.create_index("subscription_expire", sparse=True)
            await users.create_index("created_at")
            await users.create_index("last_active")
            logger.debug("✅ Users indexes created")
        except Exception as e:
            logger.warning(f"Users indexes warning: {e}")
        
        # Movies collection indexes
        if 'movies' not in collections:
            await self._db.create_collection('movies')
        
        movies = self._db.movies
        try:
            await movies.create_index("movie_code", unique=True)
            await movies.create_index("message_id")
            await movies.create_index("file_id")
            await movies.create_index([("request_count", -1)])  # For most requested
            await movies.create_index([("created_at", -1)])     # For newest
            await movies.create_index("is_active")
            logger.debug("✅ Movies indexes created")
        except Exception as e:
            logger.warning(f"Movies indexes warning: {e}")
        
        # Payments collection indexes
        if 'payments' not in collections:
            await self._db.create_collection('payments')
        
        payments = self._db.payments
        try:
            await payments.create_index("payment_id", unique=True)
            await payments.create_index("user_id")
            await payments.create_index("status")
            await payments.create_index([("created_at", -1)])
            logger.debug("✅ Payments indexes created")
        except Exception as e:
            logger.warning(f"Payments indexes warning: {e}")
        
        # Statistics collection indexes
        if 'statistics' not in collections:
            await self._db.create_collection('statistics')
        
        stats = self._db.statistics
        try:
            await stats.create_index([("date", 1), ("movie_code", 1)], unique=True)
            logger.debug("✅ Statistics indexes created")
        except Exception as e:
            logger.warning(f"Statistics indexes warning: {e}")
        
        # Channels collection (mandatory subscription)
        if 'channels' not in collections:
            await self._db.create_collection('channels')
        
        channels = self._db.channels
        try:
            await channels.create_index("channel_id", unique=True)
            await channels.create_index("is_mandatory")
            logger.debug("✅ Channels indexes created")
        except Exception as e:
            logger.warning(f"Channels indexes warning: {e}")
        
        logger.info("✅ Database indexes check completed")
    
    @property
    def db(self) -> AsyncIOMotorDatabase:
        """Get database instance"""
        if self._db is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._db
    
    # ==================== Connection Management ====================
    
    async def close(self):
        """Close database connection"""
        if self._client:
            self._client.close()
            logger.info("✅ MongoDB connection closed")
    
    async def health_check(self) -> bool:
        """Check if database is healthy"""
        try:
            await self._client.admin.command('ping')
            return True
        except Exception:
            return False
    
    # ==================== User Operations ====================
    
    async def get_or_create_user(self, user_id: int, username: str = None, 
                                  first_name: str = None, last_name: str = None) -> Dict:
        """
        Get user by ID or create if not exists
        """
        users = self.db.users
        
        user = await users.find_one({"user_id": user_id})
        
        if not user:
            # Create new user
            now = datetime.utcnow()
            today = now.date().isoformat()
            
            user = {
                "user_id": user_id,
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "created_at": now,
                "last_active": now,
                "subscription_type": "free",
                "subscription_start": None,
                "subscription_expire": None,
                "daily_requests": 0,
                "last_request_date": today,
                "total_requests": 0,
                "is_banned": False,
                "language": "uz"
            }
            await users.insert_one(user)
            logger.info(f"New user registered", extra={"user_id": user_id, "username": username})
        
        return user
    
    async def update_user(self, user_id: int, update_data: Dict) -> bool:
        """Update user data"""
        users = self.db.users
        result = await users.update_one(
            {"user_id": user_id},
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    async def increment_user_requests(self, user_id: int) -> bool:
        """Increment user's daily request count"""
        users = self.db.users
        today = datetime.utcnow().date().isoformat()
        
        # Check if it's a new day
        user = await users.find_one({"user_id": user_id})
        if not user:
            return False
        
        if user.get("last_request_date") != today:
            # Reset daily counter
            await users.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "daily_requests": 1,
                        "last_request_date": today,
                        "last_active": datetime.utcnow()
                    },
                    "$inc": {"total_requests": 1}
                }
            )
        else:
            # Increment existing counter
            await users.update_one(
                {"user_id": user_id},
                {
                    "$inc": {"daily_requests": 1, "total_requests": 1},
                    "$set": {"last_active": datetime.utcnow()}
                }
            )
        return True
    
    async def get_user_daily_requests(self, user_id: int) -> int:
        """Get user's daily request count"""
        users = self.db.users
        user = await users.find_one({"user_id": user_id})
        if not user:
            return 0
        
        # Reset if new day
        today = datetime.utcnow().date().isoformat()
        if user.get("last_request_date") != today:
            await users.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "daily_requests": 0,
                        "last_request_date": today
                    }
                }
            )
            return 0
        
        return user.get("daily_requests", 0)
    
    async def add_premium(self, user_id: int, days: int) -> bool:
        """Add premium subscription to user"""
        users = self.db.users
        now = datetime.utcnow()
        
        user = await users.find_one({"user_id": user_id})
        if not user:
            return False
        
        # Calculate new expiration
        if user.get("subscription_expire") and user["subscription_expire"] > now:
            # Extend existing subscription
            expire = user["subscription_expire"] + timedelta(days=days)
        else:
            # New subscription
            expire = now + timedelta(days=days)
        
        result = await users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "subscription_type": "premium",
                    "subscription_start": now,
                    "subscription_expire": expire
                }
            }
        )
        
        if result.modified_count:
            logger.info(f"Premium added to user", extra={"user_id": user_id, "days": days})
            return True
        return False
    
    async def remove_premium(self, user_id: int) -> bool:
        """Remove premium subscription"""
        users = self.db.users
        result = await users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "subscription_type": "free",
                    "subscription_expire": None
                }
            }
        )
        return result.modified_count > 0
    
    async def check_premium(self, user_id: int) -> bool:
        """Check if user has active premium"""
        users = self.db.users
        user = await users.find_one({"user_id": user_id})
        
        if not user or user.get("subscription_type") != "premium":
            return False
        
        # Check expiration
        expire = user.get("subscription_expire")
        if expire and expire < datetime.utcnow():
            # Subscription expired
            await users.update_one(
                {"user_id": user_id},
                {"$set": {"subscription_type": "free"}}
            )
            return False
        
        return True
    
    async def ban_user(self, user_id: int) -> bool:
        """Ban user"""
        users = self.db.users
        result = await users.update_one(
            {"user_id": user_id},
            {"$set": {"is_banned": True}}
        )
        return result.modified_count > 0
    
    async def unban_user(self, user_id: int) -> bool:
        """Unban user"""
        users = self.db.users
        result = await users.update_one(
            {"user_id": user_id},
            {"$set": {"is_banned": False}}
        )
        return result.modified_count > 0
    
    # ==================== Movie Operations ====================
    
    async def add_movie(self, movie_code: int, message_id: int, file_id: str, 
                        file_type: str, movie_name: str, caption: str = None) -> bool:
        """Add new movie to database"""
        movies = self.db.movies
        
        # Check if code exists
        existing = await movies.find_one({"movie_code": movie_code})
        if existing:
            return False
        
        movie = {
            "movie_code": movie_code,
            "message_id": message_id,
            "file_id": file_id,
            "file_type": file_type,
            "movie_name": movie_name,
            "caption": caption,
            "created_at": datetime.utcnow(),
            "request_count": 0,
            "is_active": True
        }
        
        await movies.insert_one(movie)
        logger.info(f"Movie added", extra={"movie_code": movie_code, "movie_name": movie_name})
        return True
    
    async def get_movie(self, movie_code: int) -> Optional[Dict]:
        """Get movie by code"""
        movies = self.db.movies
        movie = await movies.find_one({"movie_code": movie_code, "is_active": True})
        
        if movie:
            # Increment request count
            await movies.update_one(
                {"_id": movie["_id"]},
                {"$inc": {"request_count": 1}}
            )
            
            # Update statistics
            await self.increment_movie_stat(movie_code)
        
        return movie
    
    async def delete_movie(self, movie_code: int) -> bool:
        """Soft delete movie"""
        movies = self.db.movies
        result = await movies.update_one(
            {"movie_code": movie_code},
            {"$set": {"is_active": False}}
        )
        return result.modified_count > 0
    
    async def hard_delete_movie(self, movie_code: int) -> bool:
        """Permanently delete movie from database"""
        movies = self.db.movies
        result = await movies.delete_one({"movie_code": movie_code})
        return result.deleted_count > 0
    
    async def get_all_movies(self, page: int = 1, limit: int = 20) -> List[Dict]:
        """Get all active movies with pagination"""
        movies = self.db.movies
        skip = (page - 1) * limit
        
        cursor = movies.find({"is_active": True}).sort("created_at", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
    
    async def search_movies(self, query: str) -> List[Dict]:
        """Search movies by name"""
        movies = self.db.movies
        cursor = movies.find({
            "is_active": True,
            "movie_name": {"$regex": query, "$options": "i"}
        }).sort("request_count", -1).limit(20)
        
        return await cursor.to_list(length=20)
    
    async def get_most_requested(self, limit: int = 10) -> List[Dict]:
        """Get most requested movies"""
        movies = self.db.movies
        cursor = movies.find({"is_active": True}).sort("request_count", -1).limit(limit)
        return await cursor.to_list(length=limit)
    
    async def movie_exists(self, movie_code: int) -> bool:
        """Check if movie exists"""
        movies = self.db.movies
        count = await movies.count_documents({"movie_code": movie_code, "is_active": True})
        return count > 0
    
    async def get_movie_count(self) -> int:
        """Get total active movie count"""
        movies = self.db.movies
        return await movies.count_documents({"is_active": True})
    
    # ==================== Statistics ====================
    
    async def increment_movie_stat(self, movie_code: int):
        """Increment movie request statistic for today"""
        stats = self.db.statistics
        today = datetime.utcnow().date().isoformat()
        
        await stats.update_one(
            {"date": today, "movie_code": movie_code},
            {"$inc": {"requests": 1}},
            upsert=True
        )
    
    async def get_daily_stats(self, date: str = None) -> Dict:
        """Get daily statistics"""
        stats = self.db.statistics
        if not date:
            date = datetime.utcnow().date().isoformat()
        
        pipeline = [
            {"$match": {"date": date}},
            {
                "$group": {
                    "_id": None,
                    "total_requests": {"$sum": "$requests"},
                    "unique_movies": {"$sum": 1}
                }
            }
        ]
        
        result = await stats.aggregate(pipeline).to_list(length=1)
        return result[0] if result else {"total_requests": 0, "unique_movies": 0}
    
    async def get_total_users(self) -> int:
        """Get total user count"""
        users = self.db.users
        return await users.count_documents({})
    
    async def get_today_users(self) -> int:
        """Get users joined today"""
        users = self.db.users
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        return await users.count_documents({
            "created_at": {"$gte": today_start}
        })
    
    async def get_active_users(self, days: int = 7) -> int:
        """Get active users in last X days"""
        users = self.db.users
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        return await users.count_documents({
            "last_active": {"$gte": cutoff}
        })
    
    async def get_premium_users(self) -> int:
        """Get premium users count"""
        users = self.db.users
        return await users.count_documents({
            "subscription_type": "premium",
            "subscription_expire": {"$gt": datetime.utcnow()}
        })
    
    # ==================== Channel Operations ====================
    
    async def add_mandatory_channel(self, channel_id: str, channel_title: str, 
                                     channel_link: str) -> bool:
        """Add mandatory subscription channel"""
        channels = self.db.channels
        
        existing = await channels.find_one({"channel_id": channel_id})
        if existing:
            return False
        
        channel = {
            "channel_id": channel_id,
            "channel_title": channel_title,
            "channel_link": channel_link,
            "is_mandatory": True,
            "added_at": datetime.utcnow()
        }
        
        await channels.insert_one(channel)
        logger.info(f"Mandatory channel added", extra={"channel": channel_title})
        return True
    
    async def remove_mandatory_channel(self, channel_id: str) -> bool:
        """Remove mandatory channel"""
        channels = self.db.channels
        result = await channels.delete_one({"channel_id": channel_id})
        
        if result.deleted_count:
            logger.info(f"Mandatory channel removed", extra={"channel_id": channel_id})
            return True
        return False
    
    async def get_mandatory_channels(self) -> List[Dict]:
        """Get all mandatory channels"""
        channels = self.db.channels
        cursor = channels.find({"is_mandatory": True})
        return await cursor.to_list(length=100)
    
    # ==================== Payment Operations ====================
    
    async def create_payment(self, user_id: int, amount: float, 
                             payment_method: str, plan_days: int) -> str:
        """Create payment record"""
        payments = self.db.payments
        payment_id = f"PAY_{user_id}_{int(datetime.utcnow().timestamp())}"
        
        payment = {
            "payment_id": payment_id,
            "user_id": user_id,
            "amount": amount,
            "payment_method": payment_method,
            "plan_days": plan_days,
            "status": "pending",
            "created_at": datetime.utcnow()
        }
        
        await payments.insert_one(payment)
        return payment_id
    
    async def complete_payment(self, payment_id: str) -> bool:
        """Mark payment as completed"""
        payments = self.db.payments
        
        result = await payments.update_one(
            {"payment_id": payment_id},
            {
                "$set": {
                    "status": "completed",
                    "completed_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count:
            # Get payment details
            payment = await payments.find_one({"payment_id": payment_id})
            if payment:
                # Add premium to user
                await self.add_premium(payment["user_id"], payment["plan_days"])
                logger.info(f"Payment completed", extra={"payment_id": payment_id, "user_id": payment["user_id"]})
            return True
        
        return False
    
    async def get_user_payments(self, user_id: int) -> List[Dict]:
        """Get all payments for a user"""
        payments = self.db.payments
        cursor = payments.find({"user_id": user_id}).sort("created_at", -1)
        return await cursor.to_list(length=100)


# Create global database instance
db = Database()
