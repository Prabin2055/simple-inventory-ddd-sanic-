import uuid
from typing import Dict, Any
from pydantic import BaseModel


class User(BaseModel):
    id_: uuid.UUID
    first_name: str
    last_name: str
    email: str
    user_name: str
    password: str
    phone_number: str
    is_admin: bool = False
    is_client: bool = False

    class Config:
        extra = "forbid"
        allow_mutation = True
        title = "user"
        arbitrary_types_allowed = True

    def __hash__(self):
        return hash(self.id_)

    async def update(self, mapping: Dict[str, Any]):
        return self.copy(update=mapping)


async def user_factory(
        first_name: str,
        last_name: str,
        email: str,
        user_name: str,
        password: str,
        phone_number: str,
        is_admin: bool,
        is_client: bool,
) -> User:
    return User(
        id_=uuid.uuid4(),
        first_name=first_name,
        last_name=last_name,
        email=email,
        user_name=user_name,
        password=password,
        phone_number=phone_number,
        is_admin=is_admin,
        is_client=is_client,
    )
