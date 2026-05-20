from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> User:
        """
        Fetches an individual artist profile by their unique primary key ID.
        """
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> User:
        """
        Fetches an individual artist profile using their unique email address.
        """
        return self.db.query(User).filter(User.email == email).first()

    def create_user(self, obj_in: UserCreate, secure_password_hash: str) -> User:
        """
        Writes a brand new validated artist record directly into the users table.
        """
        db_user = User(
            email=obj_in.email,
            hashed_password=secure_password_hash,
            artist_name=obj_in.artist_name,
            role_type=obj_in.role_type,
            tenant_id=obj_in.tenant_id,
        )
        self.db.add(db_user)
        self.db.commit()      # Permanently save the transaction
        self.db.refresh(db_user)  # Refresh our object to include its new auto-generated ID
        return db_user