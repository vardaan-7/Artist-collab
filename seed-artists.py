import random
from faker import Faker
from app.core.database import SessionLocal
from app.models.user import User  
from app.core.security import SecurityManager 

fake = Faker('en_IN')  # Indian profile data generator
global_fake = Faker()   # International profile data generator

#Expanded 16-Role Creative Roster 
ROLES = [
    "rapper", "producer", "vocalist", "guitarist", "drummer", "keyboardist",
    "mixing_engineer", "mastering_engineer", "lyricist", "beatmaker", 
    "bass_player", "dj", "sound_designer", "session_singer", "manager", "cover_artist"
]

# Indian Hub Matrix (80% of Users)
INDIAN_HUBS = [
    {"name": "Noida/Delhi NCR", "lat": 28.62, "lon": 77.36},
    {"name": "Mumbai", "lat": 19.07, "lon": 72.87},
    {"name": "Bangalore", "lat": 12.97, "lon": 77.59},
    {"name": "Guwahati", "lat": 26.14, "lon": 91.73},
    {"name": "Punjab (Chandigarh)", "lat": 30.73, "lon": 76.77},
    {"name": "Chennai", "lat": 13.08, "lon": 80.27}
]

#International Hub Matrix (20% of Users)
GLOBAL_HUBS = [
    {"name": "New York, USA", "lat": 40.71, "lon": -74.00},
    {"name": "London, UK", "lat": 51.50, "lon": -0.12},
    {"name": "Tokyo, Japan", "lat": 35.67, "lon": 139.65},
    {"name": "Berlin, Germany", "lat": 52.52, "lon": 13.40},
    {"name": "Los Angeles, USA", "lat": 34.05, "lon": -118.24},
    {"name": "Atlanta, USA", "lat": 33.74, "lon": -84.38}
]

def generate_fake_artists(total_count: int = 100):
    db = SessionLocal()
    hashed_password = SecurityManager.hash_password("password123")  
    
    # Calculate distributions 
    domestic_count = int(total_count * 0.8)  # 80 Users
    international_count = total_count - domestic_count  # 20 Users
    
    print(f"🚀 Initializing high-density seeding: Injecting {total_count} advanced creators...")
    
    try:
        #Generate 80 Domestic Artists spread across India
        for i in range(domestic_count):
            hub = random.choice(INDIAN_HUBS)
            name = fake.name()
            # Generate a clean username string from the fake name
            clean_name = name.lower().replace(' ', '').replace('.', '')
            email = f"{clean_name}_{i}_{random.randint(1000,9999)}@example.com"
            role = random.choice(ROLES)
            
            # Localized scatter within ~25km radius of city hub
            latitude = hub["lat"] + random.uniform(-0.25, 0.25)
            longitude = hub["lon"] + random.uniform(-0.25, 0.25)
            
            bio = f"Hey, I'm {name}. I operate as a professional {role.replace('_', ' ')} within the active {hub['name']} scene. Open for session file swaps and remote tracking!"
            
            db_user = User(
                email=email,
                hashed_password=hashed_password,
                artist_name=name,
                role_type=role,
                tenant_id="tenant_default",
                bio=bio,
                latitude=latitude,
                longitude=longitude
            )
            db.add(db_user)

        #Generate 20 International Artists spread across the world
        for i in range(international_count):
            hub = random.choice(GLOBAL_HUBS)
            name = global_fake.name()  
            clean_name = name.lower().replace(' ', '').replace('.', '')
            email = f"{clean_name}{random.randint(10,999)}@example.com"
            role = random.choice(ROLES)
            
            # International scatter matrix configuration
            latitude = hub["lat"] + random.uniform(-0.15, 0.15)
            longitude = hub["lon"] + random.uniform(-0.15, 0.15)
            
            bio = f"What's up world! {name} here, logging into the grid from the local {hub['name']} underground loop. Looking to build bridges as a {role.replace('_', ' ')}."
            
            db_user = User(
                email=email,
                hashed_password=hashed_password,
                artist_name=name,
                role_type=role,
                tenant_id="tenant_default",
                bio=bio,
                latitude=latitude,
                longitude=longitude
            )
            db.add(db_user)
        
        db.commit()
        print(f"🎯 Mission Complete! 100 diverse artists successfully deployed inside 'tenant_default' cluster layers.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Seeding pipeline failure: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    generate_fake_artists(100)