# Stage 1: Build dell'applicazione React
FROM node:20-alpine AS build

WORKDIR /app

# Installa pnpm
RUN npm install -g pnpm

# Copia i file di configurazione delle dipendenze
COPY pnpm-lock.yaml .
COPY apps/web/package.json .

# Installa le dipendenze
RUN pnpm install

# Copia il resto dei file dell'applicazione
COPY apps/web/ .

# Definisci variabile d'ambiente per API base URL (stringa vuota = URL relativi)
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

# Esegui la build di produzione
RUN pnpm run build

# Stage 2: Serve l'applicazione con Nginx
FROM nginx:stable-alpine AS production

# Copia i file statici buildati dallo stage precedente
COPY --from=build /app/dist /usr/share/nginx/html

# Copia la configurazione di Nginx
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf

# Espone la porta 80
EXPOSE 80

# Comando per avviare Nginx
CMD ["nginx", "-g", "daemon off;"]
