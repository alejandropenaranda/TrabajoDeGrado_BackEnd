from rest_framework import serializers
from .models import Usuario, PromedioCalificaciones,Escuela 

class AuthTokenSerializer(serializers.Serializer):
    """serializer for the user authentication objectt"""
    email = serializers.CharField()
    password = serializers.CharField(
        style={'input_type': 'password'},
        trim_whitespace=False
    )

class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Escuela
        fields = ['id','nombre']

class UsuarioSerializer(serializers.ModelSerializer):
    escuela = SchoolSerializer(many=False, read_only = True)
    class Meta:
        model = Usuario
        fields = ['id', 'nombre', 'email', 'codigo', 'password', 'is_admin', 'is_director', 'is_profesor', 'escuela']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = Usuario.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            nombre=validated_data['nombre'],
            codigo=validated_data['codigo'],
            is_admin=validated_data.get('is_admin', False),
            is_director=validated_data.get('is_director', False),
            is_profesor=validated_data.get('is_profesor', False)
        )
        return user

class AverageGradesSerizalizer(serializers.ModelSerializer):
    class Meta:
        model = PromedioCalificaciones
        fields = ['id','periodo','docente_id','promedio','promedio_cuant','promedio_cual']

