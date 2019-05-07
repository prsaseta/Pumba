from django.apps import AppConfig

class GameConfig(AppConfig):
    name = 'game'
    # Borra de la memoria todas las partidas cuando el servidor arranca
    def ready(self):
        # Da error al intentar migrar
        try:
            from game.models import GameKey
            deletions = GameKey.objects.all().delete()
            print("Borrando partidas de la BD colgadas al reiniciar el servidor: " + str(deletions))
        except Exception as e:
            print("Error borrando la BD de partidas: " + str(e))