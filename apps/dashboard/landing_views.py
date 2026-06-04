from django.shortcuts import render


def inicio_view(request):
    """Página de inicio pública de Conéctate."""
    return render(request, 'landing/inicio.html')
