from lib.db_connection import DbConnection
from lib import repository
from user_components.user.adapters import orm
from user_components.user.domain import model


class UserSqlRepository(repository.SqlAlchemyRepository):
    def __init__(self, db: DbConnection):
        super().__init__(db)

    async def _add(self, model: model.User):
        await self.db.execute(
            query=orm.user.insert(),
            values={
                "id": model.id_,
                "first_name": model.first_name,
                "last_name": model.last_name,
                "email": model.email,
                "phone_number": model.phone_number,
                "user_name": model.user_name,
                "password": model.password,
                "is_admin": model.is_admin,
                "is_client": model.is_client,
            }
        )

    async def get(self, email: str):
        return await self.db.fetch_one(
            query=orm.user.select().where(orm.user.c.email == email)
        )

    async def activate_user(self, email: str):
        await self.db.execute(
            query=orm.user.update().where(orm.user.c.email == email),
            values={"is_active": True},
        )

    async def get_validated_user(self, email: str):
        user = await self.db.fetch_one(
            query=orm.user.select().where(orm.user.c.email == email)
        )
        return user

    async def change_password(self, model: model.User):
        await self.db.execute(
            query=orm.user.update().where(orm.user.c.email == model.email),
            values={"password": model.password}
        )

    async def user_email_exists(self, email: str):
        return (
                await self.db.fetch_val(orm.user.select().where(orm.user.c.email == email))
                is not None
        )
