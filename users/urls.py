from django.urls import path,include
from rest_framework.routers import SimpleRouter
from users.views import RegisterViewSet,ProcessLoginOTP,LoginViewSet,LogoutViewSet,MyDetails


router = SimpleRouter()

router.register(r"register",RegisterViewSet,basename="register")
router.register(r"loginotp",ProcessLoginOTP,basename="sendotp")
router.register(r"login",LoginViewSet,basename="login")
router.register(r"logout",LogoutViewSet,basename="login")
router.register(r"me",MyDetails,basename="myself")

myself=MyDetails.as_view({'patch':'partial_update'})

urlpatterns = [
    path(r"",include(router.urls)),
    #path(r'me',myself,name='myself')
]
