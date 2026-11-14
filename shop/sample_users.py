from shop.config import DATABASE_PATH
from shop.errors import NotFoundUserError
from shop.models import UserRole
from shop.service import ShopService
from shop.storage import SQLiteStore

SAMPLE_USERS = (
    ("admin", "admin", "123", UserRole.ADMIN),
    ("seller", "seller", "123", UserRole.SELLER),
    ("buyer", "buyer", "123", UserRole.BUYER),
)


def create_sample_users(service):
    for name, username, password, role in SAMPLE_USERS:
        try:
            service.get_user_by_username(username)
        except NotFoundUserError:
            service.add_user(name, username, password, role)
            print(f"Created {username}")
        else:
            print(f"Skipped {username}: already exists")


def main():
    create_sample_users(ShopService(SQLiteStore(DATABASE_PATH)))


if __name__ == "__main__":
    main()
