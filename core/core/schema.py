import graphene
from userManage.schema import Query as UserQuery
from userManage.schema import Mutation as UserMutation
from ecommerce.schema import Query as EcommerceQuery 
from ecommerce.schema import Mutation as EcommerceMutation
from payment.schema import Mutation as PaymentMutation

class Query(UserQuery,EcommerceQuery, graphene.ObjectType):
    pass

class Mutation(UserMutation,EcommerceMutation,PaymentMutation, graphene.ObjectType):
    pass

schema = graphene.Schema(query=Query, mutation=Mutation)