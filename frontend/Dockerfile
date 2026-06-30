FROM node:22-slim

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy source code
COPY . .

# Expose port
EXPOSE 5173

# Run dev server with host flag to expose it outside the container
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
