FROM nginx:1.25-alpine

# Install OpenSSL for SSL certificate generation
RUN apk add --no-cache openssl

# Create SSL certificate directory
RUN mkdir -p /etc/nginx/ssl

# Generate self-signed SSL certificate (for development)
RUN openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/nginx.key \
    -out /etc/nginx/ssl/nginx.crt \
    -subj "/C=US/ST=California/L=San Francisco/O=WrenchAI/CN=localhost"

# Remove default Nginx configuration
RUN rm /etc/nginx/conf.d/default.conf

# Copy our custom configuration
COPY conf.d/default.conf /etc/nginx/conf.d/

# Create directory for error pages
RUN mkdir -p /usr/share/nginx/html

# Copy custom error pages (if they exist)
COPY error_pages/ /usr/share/nginx/html/error_pages/

# Expose ports
EXPOSE 80 443

# Start Nginx
CMD ["nginx", "-g", "daemon off;"] 