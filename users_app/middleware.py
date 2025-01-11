# users_app/middleware.py

from django.utils.deprecation import MiddlewareMixin

class NoCacheMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'  # For HTTP/1.0 compatibility
        response['Expires'] = '0'  # Proxies
        return response