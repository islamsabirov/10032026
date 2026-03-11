"""
Async MongoDB database manager with connection pooling and indexes.
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
            # Create MongoDB client with connection pooling
            self._client = AsyncIOMotorClient(
                config.MONGODB_URI,
                maxPoolSize=50,
                minPoolSize=10,
                maxIdleTimeMS=30000,
                connectTimeoutMS=5000,
                serverSelectionTimeoutMS=5000
            )
            
            # Test connection
            await self._client.admin.command('ping')
            
            # Get database
            self._db = self._client[config.MONGODB_DB_NAME]
            
            # Create indexes
            await self._create_indexes()
            
            logger.info("✅ MongoDB connected successfully")
            
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            raise
    
    async def _create_indexes(self):
        """Create all database indexes for performance"""
        
        # Users collection indexes
        users = self._db.users
        await users.create_index("user_id", unique=True)
        await users.create_index("username")
        await users.create_index("subscription_expire")
        await users.create_index("created_at")
        
        # Movies collection indexes
        movies = self._db.movies
        await movies.create_index("movie_code", unique=True)
        await movies.create_index("message_id")
        await movies.create_index("file_id")
        await movies.create_index("request_count", -1)  # For most requested
        await movies.create_index("created_at", -1)     # For newest
        
        # Payments collection indexes
        payments = self._db.payments
        await payments.create_index("payment_id", unique=True)
        await payments.create_index("user_id")
        await payments.create_index("status")
        await payments.create_index("created_at", -1)
        
        # Statistics collection indexes
        stats = self._db.statistics
        await stats.create_index("date", unique=True)
        await stats.create_index("movie_code")
        
        # Channels collection (mandatory subscription)
        channels = self._db.channels
        await channels.create_index("channel_id", unique=True)
        await channels.create_index("is_mandatory")
        
        logger.info("✅ Database indexes created")
    
    @property
    def db(self) -> AsyncIOMotorDatabase:
        """Get database instance"""
        if self._db is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._db
    
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
            user = {
                "user_id": user_id,
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "created_at": datetime.utcnow(),
                "last_active": datetime.utcnow(),
                "subscription_type": "free",
                "subscription_start": None,
                "subscription_expire": None,
                "daily_requests": 0,
                "last_request_date": datetime.utcnow().date().isoformat(),
                "total_requests": 0,
                "is_banned": False,
                "language": "uz"
            }
            await users.insert_one(user)
            logger.info(f"New user registered", user_id=user_id, username=username)
        
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
        if user and user.get("last_request_date") != today:
            # Reset daily counter
            await users.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "daily_requests": 1,
                        "last_request_date": today
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
            logger.info(f"Premium added to user", user_id=user_id, days=days)
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
        logger.info(f"Movie added", movie_code=movie_code, movie_name=movie_name)
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
        
        result = await stats.aggregate(pipeline).to_list(1)
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
        return True
    
    async def remove_mandatory_channel(self, channel_id: str) -> bool:
        """Remove mandatory channel"""
        channels = self.db.channels
        result = await channels.delete_one({"channel_id": channel_id})
        return result.deleted_count > 0
    
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
            return True
        
        return False


# Create global database instance
db = Database()
