from pumba.settings import STATIC_URL
# Dada una request de un cliente (o una redirección), recoge los campos más importantes para un contexto básico
def getBasicContext(request):
    # Contexto vacío
    context = {}
    # Mensajes de error
    error = request.GET.get("error", None)
    context["error"] = error
    # Notificaciones
    notification = request.GET.get("notification", None)
    context["notification"] = notification
    # Camino a recursos estáticos (algunas vistas, por hacerlo con jQuery o parecido, no pueden usar el {% static %})
    context["static_path"] = STATIC_URL
    
    return context

