from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class Escuela(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_admin', True)
        extra_fields.setdefault('is_director', False)
        extra_fields.setdefault('is_profesor', False)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, password, **extra_fields)

class Usuario(AbstractBaseUser, PermissionsMixin):
    codigo = models.CharField(max_length=100, unique=True)
    nombre = models.CharField(max_length=50)
    email = models.EmailField(max_length=250, unique=True)
    is_admin = models.BooleanField(default=False)
    is_director = models.BooleanField(default=False)
    is_profesor = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    escuela = models.ForeignKey(Escuela, on_delete=models.CASCADE, null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['codigo']

    def __str__(self):
        return f"{self.nombre} ({self.email})"

    @property
    def is_staff(self):
        return self.is_admin

class Materia(models.Model):
    codigo = models.CharField(max_length=100, unique=True)
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre

class CalificacionesCualitativas(models.Model):
    docente = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='calificaciones_cualitativas')
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    periodo = models.CharField(max_length=20)
    comentario = models.TextField()
    comentario_limpio = models.TextField(blank=True, null=True)
    promedio = models.FloatField()

    def __str__(self):
        return self.comentario

class CalificacionesCuantitativas(models.Model):
    docente = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='calificaciones_cuantitativas')
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    periodo = models.CharField(max_length=20)
    pregunta_9 = models.FloatField()
    pregunta_10 = models.FloatField()
    pregunta_11 = models.FloatField()
    pregunta_12 = models.FloatField()
    pregunta_13 = models.FloatField()
    pregunta_14 = models.FloatField()
    pregunta_15 = models.FloatField()
    pregunta_16 = models.FloatField()
    pregunta_17 = models.FloatField()
    pregunta_18 = models.FloatField()
    pregunta_19 = models.FloatField()
    pregunta_20 = models.FloatField()
    promedio = models.FloatField()

class PromedioCalificaciones(models.Model):
    docente = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='promedios_calificaciones')
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    promedio = models.FloatField()
    promedio_cual = models.FloatField()
    promedio_cuant = models.FloatField()
    prom_pregunta_9 = models.FloatField(default=0)
    prom_pregunta_10 = models.FloatField(default=0)
    prom_pregunta_11 = models.FloatField(default=0)
    prom_pregunta_12 = models.FloatField(default=0)
    prom_pregunta_13 = models.FloatField(default=0)
    prom_pregunta_14 = models.FloatField(default=0)
    prom_pregunta_15 = models.FloatField(default=0)
    prom_pregunta_16 = models.FloatField(default=0)
    prom_pregunta_17 = models.FloatField(default=0)
    prom_pregunta_18 = models.FloatField(default=0)
    prom_pregunta_19 = models.FloatField(default=0)
    prom_pregunta_20 = models.FloatField(default=0)
    periodo = models.CharField(max_length=20)

class FortalezasDebilidadesCuantitativas(models.Model):
    docente = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='fortalezas_debilidades_cuantitativas')
    prom_pregunta_9 = models.FloatField(default=0)
    prom_pregunta_10 = models.FloatField(default=0)
    prom_pregunta_11 = models.FloatField(default=0)
    prom_pregunta_12 = models.FloatField(default=0)
    prom_pregunta_13 = models.FloatField(default=0)
    prom_pregunta_14 = models.FloatField(default=0)
    prom_pregunta_15 = models.FloatField(default=0)
    prom_pregunta_16 = models.FloatField(default=0)
    prom_pregunta_17 = models.FloatField(default=0)
    prom_pregunta_18 = models.FloatField(default=0)
    prom_pregunta_19 = models.FloatField(default=0)
    prom_pregunta_20 = models.FloatField(default=0)
    valoraciones = models.JSONField()
    