from django.test import TestCase
from django.contrib.auth.models import User
from django.test import Client
from pumba import settings
from django.core import mail
from authentication.models import PreRegister

# Create your tests here.

class LoginTestCase(TestCase):
    def setUp(self):
        user1 = User.objects.create_user("john1", "john1@gmail.com", "john1")
        user2 = User.objects.create_user("john2", "john2@gmail.com", "john2")

    def test_get_form(self):
        # Comprueba que una petición GET devuelve un 200
        c = Client()
        response = c.get("/authentication/login/")
        self.assertTrue(response.status_code == 200)

    def test_already_authenticated(self):
        # Comprueba que redirige si se está ya autenticado
        c = Client()
        c.login(username='john1', password='john1')
        response = c.post('/authentication/login/', {'username': 'john1', 'password': 'john1'})
        self.assertTrue(response.status_code == 302)

    def test_correct_login(self):
        # Si se loguea correctamente, dará un 302 redirect
        c = Client()
        response = c.post('/authentication/login/', {'username': 'john1', 'password': 'john1'})
        self.assertTrue(response.status_code == 302)

    def test_incorrect_login(self):
        # Si no se loguea correctamente, dará un 200 
        c = Client()
        response = c.post('/authentication/login/', {'username': 'john1', 'password': 'xxx'})
        self.assertTrue(response.status_code == 200)
        self.assertTrue(response.context['error'])

    def test_incorrect_form(self):
        # Si no se loguea correctamente, dará un 200 
        c = Client()
        response = c.post('/authentication/login/', {'username': 'john1', 'password': ''})
        self.assertTrue(response.status_code == 200)
        self.assertTrue(response.context['error'])

class RegisterTestCase(TestCase):
    def setUp(self):
        # Nos aseguramos de que la verificación está activada
        #settings.IS_USING_EMAIL_VERIFICATION_FOR_REGISTRY = True
        # Usuario de prueba para comprobar conflictos
        user2 = User.objects.create_user("john2", "john2@gmail.com", "john2")
    
    def test_correct_register(self):
        # Registro correcto
        # 1. Registrarse
        # 2. Verificar
        # 3. Loguearse
        c = Client()
        # 1. Registrarse
        response = c.post('/authentication/register/', {'username': 'john1', 'password': 'john1', 'confirm': 'john1', 'email': 'john1@gmail.com'})
        if(settings.IS_USING_EMAIL_VERIFICATION_FOR_REGISTRY):
            self.assertTrue(response.status_code == 200)
            self.assertIsNone(response.context.get('error'))
            self.assertEqual(len(mail.outbox), 1)
        else:
            self.assertTrue(response.status_code == 302)

        # 2. Verificar
        # Vamos a hacer un poco de trampa y coger directamente de la BD el código
        preregister = PreRegister.objects.get(username = 'john1')
        response2 = c.post('/authentication/verification/?id='+preregister.verification)
        self.assertTrue(response2.status_code == 200)

        # 3. Loguearse
        response3 = c.post('/authentication/login/', {'username': 'john1', 'password': 'john1'})
        self.assertTrue(response3.status_code == 302)

    def test_incorrect_email(self):
        # Nos registramos con un correo repetido
        c = Client()
        response = c.post('/authentication/register/', {'username': 'john1', 'password': 'john1', 'confirm': 'john1', 'email': 'john2@gmail.com'})
        self.assertTrue(response.status_code == 200)
        self.assertEqual(response.context.get('error'), "That email is already taken")

    def test_incorrect_username(self):
        # Nos registramos con un usuario repetido
        c = Client()
        response = c.post('/authentication/register/', {'username': 'john2', 'password': 'john1', 'confirm': 'john1', 'email': 'john1@gmail.com'})
        self.assertTrue(response.status_code == 200)
        self.assertEqual(response.context.get('error'), "That username is already taken")

    def test_incorrect_password(self):
        # Nos registramos con una contraseña que no coincide
        c = Client()
        response = c.post('/authentication/register/', {'username': 'john1', 'password': 'john1', 'confirm': 'xxx', 'email': 'john1@gmail.com'})
        self.assertTrue(response.status_code == 200)
        self.assertEqual(response.context.get('error'), "Passwords don't match")

    def test_empty_username(self):
        # Nos registramos sin nombre de usuario
        c = Client()
        response = c.post('/authentication/register/', {'username': '', 'password': 'john1', 'confirm': 'john1', 'email': 'john1@gmail.com'})
        self.assertTrue(response.status_code == 200)
        self.assertEqual(response.context.get('error'), "Invalid data")

    def test_empty_password(self):
        # Nos registramos sin contraseña
        c = Client()
        response = c.post('/authentication/register/', {'username': 'john1', 'password': '', 'confirm': '', 'email': 'john1@gmail.com'})
        self.assertTrue(response.status_code == 200)
        self.assertEqual(response.context.get('error'), "Invalid data")

    def test_empty_email(self):
        # Nos registramos sin correo
        c = Client()
        response = c.post('/authentication/register/', {'username': 'john1', 'password': 'john1', 'confirm': 'john1', 'email': ''})
        self.assertTrue(response.status_code == 200)
        self.assertEqual(response.context.get('error'), "Invalid data")

    def test_incorrect_verification(self):
        # Intentamos verificar algo que no existe
        c = Client()
        response = c.post('/authentication/verification/?id=' + 'test')
        self.assertTrue(response.status_code == 400)

    def test_empty_verification(self):
        # Intentamos verificar sin mandar el parámetro
        c = Client()
        response = c.post('/authentication/verification/')
        self.assertTrue(response.status_code == 400)