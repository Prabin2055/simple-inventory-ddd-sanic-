import jwt
import random

import jwt
from sanic import Sanic
from user_components.user.domain import command
from lib import unit_of_work
from user_components.user.domain import handler, model
from user_components.user.domain import events
from entrypoint.redis_config.cache import caches
from user_components.user.domain import exceptions
from user_components.user.utils import password_manager

app = Sanic.get_app()


async def generate_otp():
    return str(random.randint(111111, 999999))


async def add_user(
        validated_data: command.AddUser, uow: unit_of_work.SqlAlchemyUnitOfWork
):
    async with uow:
        user_exists = await uow.repository.user_email_exists(validated_data.email)
        if user_exists:
            raise exceptions.UserExists("User is already exist")
        else:
            user = await handler.add_user(validated_data)
            password_hash = await password_manager.generate_password(user.password)
            await user.set_password(password_hash)
            await uow.repository.add(user)
            otp = await generate_otp()
            uow.events.add(
                events.OTPSent(
                    phone_number=validated_data.phone_number,
                    email=validated_data.email,
                    otp=otp,
                )
            )
        return otp


async def activate_user(
        validated_data: command.ActivateUser,
        uow: unit_of_work.SqlAlchemyUnitOfWork,
):
    async with uow:
        cache = caches.get("redis_cache")
        otp = await cache.get(validated_data.email)
        if not otp:
            raise exceptions.OTP_NOT_FOUND
        if validated_data.otp == otp:
            await uow.repository.activate_user(validated_data.email)
            await cache.delete(validated_data.email)
        else:
            raise exceptions.OTP_MISMATCHED


async def login_user(
        validated_data: command.LoginUser,
        uow: unit_of_work.SqlAlchemyUnitOfWork,
):
    async with uow:
        user = await uow.repository.get_validated_user(validated_data.email)
        if not user:
            raise exceptions.USERDOESNOTEXIST
        if not user["is_active"]:
            raise exceptions.USER_NOT_ACTIVE
        if await password_manager.check_password(
                user["password"], validated_data.password
        ):
            from sanic import Sanic
            app = Sanic.get_app()
            current_user = {
                "id": str(user["id"]),
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "email": user["email"],
                "phone_number": user["phone_number"],
                "is_admin": user["is_admin"],
                "is_client": user["is_client"],

            }
            token = jwt.encode(
                payload=current_user,
                key=app.ctx.settings.secret_key,
                algorithm="HS256",
            )
            return {"token": token, "user": current_user}
        else:
            raise exceptions.PASSWORD_INCORRECT


async def change_password(
        validated_data: command.ChangePassword,
        uow: unit_of_work.SqlAlchemyUnitOfWork,
):
    async  with uow:
        current_user = await uow.repository.get_validated_user(
            email=validated_data.email
        )
        if current_user:
            if await password_manager.check_password(
                    current_user["password"], validated_data.password,
            ):
                user = model.User(
                    id_=current_user["id"],
                    first_name=current_user["first_name"],
                    last_name=current_user["last_name"],
                    email=current_user["email"],
                    user_name=current_user["user_name"],
                    password=current_user["password"],
                    phone_number=current_user["phone_number"],
                    is_admin=current_user["is_admin"],
                    is_client=current_user["is_client"],
                )
                cmd = command.ChangePassword(
                    user=user,
                    email=user.email,
                    password=validated_data.password,
                    new_password=validated_data.new_password,
                    new_password_re=validated_data.new_password_re,
                )
                user_model = await handler.change_password(cmd)
                password_hash = await password_manager.generate_password(
                    user_model.password
                )
                await user_model.set_password(password_hash)
                await uow.repository.change_password(user_model)
            else:
                raise exceptions.PASSWORD_INCORRECT
        else:
            raise exceptions.USERDOESNOTEXIST


async def forget_password(
        validated_data: command.ForgetPassword,
        uow: unit_of_work.SqlAlchemyUnitOfWork,
):
    async with uow:
        current_user = await uow.repository.get_validated_user(
            email=validated_data.email
        )
        if not current_user:
            raise exceptions.USERDOESNOTEXIST
        else:
            otp = await generate_otp()
            uow.events.add(
                events.OTPSent(
                    phone_number=current_user["phone_number"],
                    email=current_user["email"],
                    otp=otp,
                )
            )
        return otp


async def forget_password_update(
        validated_data: command.ForgetPasswordUpdate,
        uow: unit_of_work.SqlAlchemyUnitOfWork,
):
    async with uow:
        cache = caches.get("redis_cache")
        if not cache:
            raise exceptions.REDIS_CONNECTION_NOT_ESTABLISHED
        current_user = await uow.repository.get_validated_user(
            email=validated_data.email
        )
        if not current_user:
            raise exceptions.USERDOESNOTEXIST
        otp = await cache.get(validated_data.email)
        if not otp:
            raise exceptions.OTP_NOT_FOUND
        if validated_data.otp == otp:
            await  cache.delete(validated_data.email)
            user = model.User(
                id_=current_user["id"],
                first_name=current_user["first_name"],
                last_name=current_user["last_name"],
                email=current_user["email"],
                user_name=current_user["user_name"],
                password=current_user["password"],
                phone_number=current_user["phone_number"],
                is_admin=current_user["is_admin"],
                is_client=current_user["is_client"],
            )
            cmd = command.ForgetPasswordUpdate(
                user=user,
                email=user.email,
                otp=validated_data.otp,
                password_new=validated_data.password_new,
                password_new_re=validated_data.password_new_re,
            )
            user_model = await handler.change_password(cmd)
            password_hash = await password_manager.generate_password(
                user_model.password
            )
            await user_model.set_password(password_hash)
            await uow.repository.change_password(user_model)
        else:
            raise exceptions.OTP_MISMATCHED
