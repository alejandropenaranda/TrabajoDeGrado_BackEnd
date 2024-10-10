from rest_framework import serializers
from .models import FortalezasDebilidadesCualitativas, FortalezasDebilidadesEscula, Usuario, PromedioCalificaciones,Escuela,FortalezasDebilidadesCuantitativas, Materia, CalificacionesCualitativas

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
    escuela_id = serializers.PrimaryKeyRelatedField(queryset=Escuela.objects.all(), write_only=True)
    escuela = SchoolSerializer(read_only=True)

    class Meta:
        model = Usuario
        fields = ['id', 'nombre', 'email', 'codigo', 'password', 'is_admin', 'is_director', 'is_profesor', 'escuela_id', 'escuela']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        escuela_instance = validated_data.pop('escuela_id')
        user = Usuario.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            nombre=validated_data['nombre'],
            codigo=validated_data['codigo'],
            escuela=escuela_instance,
            is_admin=validated_data.get('is_admin', False),
            is_director=validated_data.get('is_director', False),
            is_profesor=validated_data.get('is_profesor', False)
        )
        return user

class SubjectSerialize(serializers.ModelSerializer):
    class Meta:
        model = Materia
        fields = ['id','codigo', 'nombre']


class AverageGradesSerizalizer(serializers.ModelSerializer):
    docente_nombre = serializers.SerializerMethodField()
    escuela = serializers.SerializerMethodField()
    materia = SubjectSerialize(many = False, read_only=True)
    class Meta:
        model = PromedioCalificaciones
        fields = ['id', 'periodo', 'docente_id', 'promedio', 'promedio_cuant', 'promedio_cual', 'materia', 'docente_nombre', 'escuela']

    def get_docente_nombre(self, obj):
        return obj.docente.nombre if obj.docente else None

    def get_escuela(self, obj):
        return obj.docente.escuela.nombre if obj.docente and obj.docente.escuela else None

class CuantFortDebSerializer(serializers.ModelSerializer):
    class Meta:
        model = FortalezasDebilidadesCuantitativas
        fields = ['id', 'docente_id', 'valoraciones']


class CualFortDebSerializer(serializers.ModelSerializer):
    class Meta:
        model = FortalezasDebilidadesCualitativas
        fields = ['id', 'docente_id', 'valoraciones']

class CalificacionesCualitativasSerializer(serializers.ModelSerializer):
    materia = SubjectSerialize(many = False, read_only=True)
    class Meta:
        model = CalificacionesCualitativas
        fields = ['docente_id', 'materia', 'periodo', 'comentario', 'promedio']

class Top10Serializer(serializers.ModelSerializer):
    docente_nombre = serializers.CharField(source='docente.nombre')

    class Meta:
        model = PromedioCalificaciones
        fields = ['docente_nombre', 'promedio']

class SchoolFortDebSerializer(serializers.ModelSerializer):
    class Meta:
        model = FortalezasDebilidadesEscula
        fields = ['id', 'escuela_id', 'valoraciones']
