# 1. Base Image
# Use a lightweight Node.js 20 environment based on Alpine Linux.
FROM node:20-alpine

# 2. Working Directory
# Define the working folder inside the container.
WORKDIR /app

# 3. Copy Dependency Manifests
# Copy package files to install packages.
COPY package*.json ./

# 4. Install Dependencies
# Run npm install to install packages inside the container.
RUN npm install

# 5. Copy Frontend Files
# Copy the rest of the React source code and asset configurations.
COPY . .

# 6. Expose Port
# Expose the default Vite server development port.
EXPOSE 5173

# 7. Start Command
# Run Vite with --host flag so it exposes its port outside of the container network.
CMD ["npm", "run", "dev", "--", "--host"]
