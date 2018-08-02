from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser

#重置用户信息字段
class ReUser(AbstractUser):
	avatar = models.ImageField(upload_to='AvatarImage',blank=True,default='AvatarImage/default.png')
	apikey = models.CharField(max_length=256,blank=True)
	Secret = models.CharField(max_length=256,blank=True,)

	def __str__(self):
		return self.username


