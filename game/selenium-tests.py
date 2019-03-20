from django.test import TestCase, LiveServerTestCase
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from channels.testing import ChannelsLiveServerTestCase
from game.domain_objects import *
from django.core.cache import cache 
from django.contrib.auth.models import User
import game.matchmaking
import time
from selenium import webdriver
from game.models import GameKey

class DriverTestCase(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user("test1", "testuser1@gmail.com", "test1")
        self.user2 = User.objects.create_user("test2", "testuser2@gmail.com", "test2")
        self.user3 = User.objects.create_user("test3", "testuser3@gmail.com", "test3")
        self.user4 = User.objects.create_user("test4", "testuser4@gmail.com", "test4")
    # Comprueba que ChromeDriver funciona
    def test(self):
        #driver = webdriver.Chrome("C:\Program Files\Chromedriver\chromedriver.exe")  # Optional argument, if not specified will search path.
        #driver.get('http://www.google.com/xhtml')
        #time.sleep(5) # Let the user actually see something!
        #search_box = driver.find_element_by_name('q')
        #search_box.send_keys('ChromeDriver')
        #search_box.submit()
        #time.sleep(5) # Let the user actually see something!
        #driver.quit()
        pass
    
    # Intenta autenticarse en dos ventanas diferentes
    def test_login(self):
        driver1 = webdriver.Chrome("C:\Program Files\Chromedriver\chromedriver.exe")
        driver2 = webdriver.Chrome("C:\Program Files\Chromedriver\chromedriver.exe")

        driver1.get('http://localhost:8000/authentication/login/')
        driver2.get('http://localhost:8000/authentication/login/')

        username1 = driver1.find_element_by_id("id_username")
        password1 = driver1.find_element_by_id("id_password")
        username1.send_keys("test1")
        password1.send_keys("test1")
        password1.submit()

        username2 = driver2.find_element_by_id("id_username")
        password2 = driver2.find_element_by_id("id_password")
        username2.send_keys("test2")
        password2.send_keys("test2")
        password2.submit()

        time.sleep(10)
        driver1.quit()
        driver2.quit()

    def test_create_match(self):
        # Se loguea, se une a una partida y comprueba que se envía bien un mensaje de chat
        # Abre dos clientes
        driver1 = webdriver.Chrome("C:\Program Files\Chromedriver\chromedriver.exe")
        driver2 = webdriver.Chrome("C:\Program Files\Chromedriver\chromedriver.exe")

        # Se loguea con ambos clientes
        driver1.get('http://localhost:8000/authentication/login/')
        driver2.get('http://localhost:8000/authentication/login/')

        username1 = driver1.find_element_by_id("id_username")
        password1 = driver1.find_element_by_id("id_password")
        username1.send_keys("test1")
        password1.send_keys("test1")
        password1.submit()

        username2 = driver2.find_element_by_id("id_username")
        password2 = driver2.find_element_by_id("id_password")
        username2.send_keys("test2")
        password2.send_keys("test2")
        password2.submit()

        # Va a la vista de matchmaking
        driver1.get('http://localhost:8000/game/matchmaking/')
        # Le da al botón de crear partida
        form = driver1.find_element_by_id("create-match-form")
        form.submit()
        # Recupera la ID de la partida
        #time.sleep(2)
        id = driver1.execute_script('return roomName')

        # El otro cliente entra en la partida con la ID recuperada
        driver2.get('http://localhost:8000/game/join/?id=' + str(id))
        # Le damos tiempo a conectarse
        time.sleep(3)

        # El primer cliente envía un mensaje de chat
        chat_input = driver1.find_element_by_id("chat-message-input")
        chat_input.send_keys("PROBANDO")
        driver1.execute_script("document.querySelector('#chat-message-submit').onclick()")

        # El segundo cliente envía un mensaje de chat
        chat_input = driver2.find_element_by_id("chat-message-input")
        chat_input.send_keys("TESTEANDO")
        driver2.execute_script("document.querySelector('#chat-message-submit').onclick()")

        # Esperamos a que a los mensajes les de tiempo de ir y venir
        time.sleep(2)

        # Vemos si han llegado correctamente
        chatbox = driver1.find_element_by_id("chat-log")
        text = chatbox.get_property('value')
        self.assertTrue("PROBANDO" in text)

        chatbox = driver2.find_element_by_id("chat-log")
        text = chatbox.get_property('value')
        self.assertTrue("PROBANDO" in text)

        chatbox = driver1.find_element_by_id("chat-log")
        text = chatbox.get_property('value')
        self.assertTrue("TESTEANDO" in text)

        chatbox = driver2.find_element_by_id("chat-log")
        text = chatbox.get_property('value')
        self.assertTrue("TESTEANDO" in text)

        time.sleep(2)

        driver1.quit()
        driver2.quit()

    # Este test no se puede hacer por los siguientes motivos:
    # 1. Usando el TestCase normal, no usa la BD de testeo, por lo que es impredecible los resultados
    # que dará empezar la partida y no se pueden comprobar inputs específicos
    # 2. Usando LiveTestCase Channels no funciona
    # 3. Usando ChannelsLiveTestCase deja de funcionar enteramente y no he encontrado una solución por
    # ningún lado.
    # Se ha intentado, pero viendo como el test era muy simple y de todas maneras la interfaz que prueba 
    # es, valga la redundancia, de testeo, tampoco se pierde mucho.
    def test_play_match(self):
        # Juega una partida "falsa"
        # Abre dos clientes
        driver1 = webdriver.Chrome("C:\Program Files\Chromedriver\chromedriver.exe")
        driver2 = webdriver.Chrome("C:\Program Files\Chromedriver\chromedriver.exe")

        # Se loguea con ambos clientes
        driver1.get('http://localhost:8000/authentication/login/')
        driver2.get('http://localhost:8000/authentication/login/')

        username1 = driver1.find_element_by_id("id_username")
        password1 = driver1.find_element_by_id("id_password")
        username1.send_keys("test1")
        password1.send_keys("test1")
        password1.submit()

        username2 = driver2.find_element_by_id("id_username")
        password2 = driver2.find_element_by_id("id_password")
        username2.send_keys("test2")
        password2.send_keys("test2")
        password2.submit()

        # Va a la vista de matchmaking
        driver1.get('http://localhost:8000/game/matchmaking/')
        # Le da al botón de crear partida
        form = driver1.find_element_by_id("create-match-form")
        form.submit()
        # Recupera la ID de la partida
        time.sleep(5)
        id = driver1.execute_script('return roomName')

        # El otro cliente entra en la partida con la ID recuperada
        driver2.get('http://localhost:8000/game/join/?id=' + str(id))
        # Le damos tiempo a conectarse
        time.sleep(3)

        # Le damos al botón de empezar partida
        driver1.execute_script("document.querySelector('#begin-match').onclick()")
        time.sleep(3)

        # Probamos que todo funciona correctamente
        chatbox = driver1.find_element_by_id("chat-log")
        text = chatbox.get_property('value')
        self.assertTrue("The match has begun!" in text)

        chatbox = driver2.find_element_by_id("chat-log")
        text = chatbox.get_property('value')
        self.assertTrue("The match has begun!" in text)


        # Hacemos trampa como quien no quiere la cosa
        #game = cache.get("match_" + str(id))
        #game.lastSuit = Suit.ESPADAS
        #game.lastNumber = CardNumber.DIVINE
        #game.players[0].hand = [Card(Suit.ESPADAS, CardNumber.DIVINE), Card(Suit.ESPADAS, CardNumber.SWITCH)]
        #game.players[1].hand = [Card(Suit.ESPADAS, CardNumber.DIVINE), Card(Suit.ESPADAS, CardNumber.SWITCH)]
        #cache.set("match_" + str(id), game, None)

        # Actualizamos a ambos jugadores
        #driver1.execute_script("document.querySelector('#update-state').onclick()")
        #driver2.execute_script("document.querySelector('#update-state').onclick()")

        # Esperamos un poco y empieza la fiesta
        #time.sleep(3)

        #driver1.execute_script("document.querySelector('#hand-play').onclick()")
        #time.sleep(1)
        #driver1.execute_script("document.querySelector('#end-turn').onclick()")
        #time.sleep(1)

        #driver2.execute_script("document.querySelector('#hand-play').onclick()")
        #time.sleep(1)
        #driver2.execute_script("document.querySelector('#end-turn').onclick()")
        #time.sleep(1)

        #driver1.execute_script("document.querySelector('#hand-play').onclick()")
        #time.sleep(1)

        #time.sleep(5)

        driver1.quit()
        driver2.quit()