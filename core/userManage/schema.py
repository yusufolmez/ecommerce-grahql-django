import graphene
from graphene_django import DjangoObjectType
from .models import CustomPermission,CustomRole,CustomUser, EmailVerification
from django.contrib.auth import authenticate
from functools import wraps
from datetime import datetime, timedelta
import jwt
from django.conf import settings
import random
from django.core.mail import send_mail

def custom_permission_required(required_permiision):
    def decoreator(func):
        @wraps(func)
        def wrapper(root,info,*args,**kwargs):
            
            user = info.context.user
            if not user.is_authenticated:
                raise Exception("Lütfen giriş yapınız.")
            if not user.has_permission(required_permiision):
                raise Exception('Yetkiniz yok')
            return func(root, info,*args,**kwargs)
        return wrapper
    return decoreator

def generate_access_token(user):
    payload = {
        'user_id':user.id,
        'exp': datetime.utcnow() + timedelta(minutes=15),
        'iat': datetime.utcnow(),
        'token_type':'access',
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

def generate_refresh_token(user):
    payload = {
        'user_id':user.id,
        'exp': datetime.utcnow() + timedelta(days=7),
        'iat': datetime.utcnow(),
        'token_type':'refresh',
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

#--------------------------------------------------------------------------------

class PermissionType(DjangoObjectType):
    class Meta:
        model = CustomPermission
        field = '__all__'

class RoleType(DjangoObjectType):
    class Meta:
        model = CustomRole
        field = '__all__'

class UserType(DjangoObjectType):
    class Meta:
        model = CustomUser
        field = ('id','username','first_name','last_name','email','phone')

class TokenType(graphene.ObjectType):
    access_token = graphene.String()
    refresh_token = graphene.String()

#--------------------------------------------------------------------------------------------------

class AuthMutation(graphene.Mutation):
    tokens = graphene.Field(TokenType)
    class Arguments:
        username = graphene.String()
        password = graphene.String()

    def mutate(self,info,username,password):
        user = authenticate(username=username,password=password)

        if user is None:
            raise Exception("Geçersiz giriş bilgileri.")
        
        access_token = generate_access_token(user)
        refresh_token = generate_refresh_token(user)

        return AuthMutation(tokens=TokenType(access_token=access_token,refresh_token=refresh_token))
    

class RegisterUserMutation(graphene.Mutation):
    user = graphene.Field(UserType)
    success = graphene.Boolean()
    message = graphene.String()

    class Arguments:
        username = graphene.String(required=True)
        email = graphene.String(required=True)
        password = graphene.String(required=True)
        phone = graphene.String(required=True)
        first_name = graphene.String()
        last_name = graphene.String()

    def mutate(self, info, username, email, password, phone, first_name=None, last_name=None):
        if CustomUser.objects.filter(email=email).exists():
            raise Exception("Bu email ile daha önce kayıt olunmuş.")

        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            phone=phone,
            first_name=first_name,
            last_name=last_name,
        )

        verification_code = str(random.randint(100000, 999999))

        EmailVerification.objects.create(user=user, code=verification_code)

        send_mail(
            subject="Email Doğrulama Kodu",
            message=f"Doğrulama kodunuz: {verification_code}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )

        return RegisterUserMutation(
            user=user,
            success=True,
            message="Kayıt başarılı. Lütfen email adresinizi doğrulamak için emailinizi kontrol edin."
        )
    
class UpdateUserMutation(graphene.Mutation):
        success = graphene.Boolean()
        user = graphene.Field(UserType)
        class Arguments:
            username = graphene.String()
            first_name = graphene.String()
            last_name = graphene.String()
            phone = graphene.String()
        
        def mutate(self,info,**kwargs):
            try:
                user = info.context.user
                if user.is_anonymous:
                    raise Exception('Lütfen giriş yapınız')
                if 'username' in kwargs:
                    user.username = kwargs['username']
                if 'first_name' in kwargs:
                    user.first_name = kwargs['first_name']
                if 'last_name' in kwargs:
                    user.last_name = kwargs['last_name']
                if 'email' in kwargs:
                    user.email = kwargs['email']
                user.save()
                return UpdateUserMutation(success=True, user=user)
            except Exception as e:
                raise Exception(str(e))
            
class DeleteUserMutation(graphene.Mutation):
    success = graphene.Boolean()
    class Arguments:
        pass

    def mutate(self,info):
        try:
            user = info.context.user
            if user.is_anonymous:
                raise Exception('Lütfen giriş yapınız.')
            user.delete()
            return DeleteUserMutation(success=True)
        except Exception as e:
            raise Exception(str(e))

class ResendVerifyEmailMutation(graphene.Mutation):
    success = graphene.Boolean()
    class Arguments:
        email = graphene.String()
        password = graphene.String()
    def mutate(self,info,email,password):
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            raise Exception("Kullanıcı bulunamadı.")
        
        if not user.check_password(password):
            raise Exception('Geçersiz şifre.')
        
        verification_code = str(random.randint(100000, 999999))

        EmailVerification.objects.create(user=user, code=verification_code)

        send_mail(
            subject="Email Doğrulama Kodu",
            message=f"Doğrulama kodunuz: {verification_code}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        return ResendVerifyEmailMutation(success=True)


class VerifyEmailMutation(graphene.Mutation):
    success = graphene.Boolean()

    class Arguments:
        code = graphene.String(required=True)

    def mutate(self, info, code):
        user = info.context.user
        if user.is_anonymous:
            raise Exception("Lütfen giriş yapınız.")
        
        try:
            email_verification = EmailVerification.objects.get(user=user)
        except EmailVerification.DoesNotExist:
            raise Exception("Doğrulama kodu bulunamadı. Lütfen tekrar deneyin.")
        
        if email_verification.code != code:
            raise Exception("Kod yanlış.")
        
        user.is_verified = True
        user.save()
        
        email_verification.delete()
        
        return VerifyEmailMutation(success=True)    

#---------------------------------------------------------------------------------------------------

class SetRoleMutation(graphene.Mutation):
    roles = graphene.Field(RoleType)
    success = graphene.Boolean()
    class Arguments:
        role_id = graphene.ID()
        user_id = graphene.ID()
    @custom_permission_required('can_set_role')
    def mutate(self,info,role_id,user_id):
        user = CustomUser.objects.get(id=user_id)
        role = CustomRole.objects.get(id=role_id)
        user.role = role
        user.save()
        return SetRoleMutation(success=True, roles=user.role)
    

#---------------------------------------------------------------------------------------------------

class Query(graphene.ObjectType):
    me = graphene.Field(UserType)

    def resolve_me(self,info):
        user = info.context.user
        if user is None or user.is_anonymous:
            raise Exception('Lütfen giriş yapınız.')
        return user
    
class Mutation(graphene.ObjectType):
    auth_token = AuthMutation.Field()
    set_role = SetRoleMutation.Field()
    register = RegisterUserMutation.Field()
    update_user = UpdateUserMutation.Field()
    delete_user = DeleteUserMutation.Field()
    verify_email = VerifyEmailMutation.Field()
    resend_verify_email = ResendVerifyEmailMutation.Field()