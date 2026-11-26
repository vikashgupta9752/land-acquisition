import os
from django.core.wsgi import get_wsgi_application

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'land_acquisition.settings')
# Ensure Vercel environment variable is set
os.environ.setdefault('VERCEL', '1')

# Initialize WSGI application once (cold start optimization)
application = get_wsgi_application()

def handler(request, context):
    """Vercel serverless entry point.
    The django_vercel package adapts the WSGI app to Vercel's request/response format.
    """
    from django_vercel import get_response
    return get_response(application, request, context)
