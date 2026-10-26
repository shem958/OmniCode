package common

import (
	"os"
	"path/filepath"

	"github.com/joho/godotenv"
)

type Config struct {
	GatewayPort       string
	RepoServicePort   string
	SearchServicePort string
	UserServicePort   string
	AIEngineURL       string
	PostgresDSN       string
}

func LoadConfig() *Config {
	// Look for .env in current, parent, or grandparent directories
	dir, err := os.Getwd()
	if err == nil {
		for {
			envPath := filepath.Join(dir, ".env")
			if _, err := os.Stat(envPath); err == nil {
				_ = godotenv.Load(envPath)
				break
			}
			parent := filepath.Dir(dir)
			if parent == dir {
				break
			}
			dir = parent
		}
	}

	return &Config{
		GatewayPort:       getEnv("GATEWAY_PORT", "8080"),
		RepoServicePort:   getEnv("REPO_SERVICE_PORT", "8081"),
		SearchServicePort: getEnv("SEARCH_SERVICE_PORT", "8082"),
		UserServicePort:   getEnv("USER_SERVICE_PORT", "8083"),
		AIEngineURL:       getEnv("AI_ENGINE_URL", "http://127.0.0.1:8000"),
		PostgresDSN:       getPostgresDSN(),
	}
}

func getEnv(key, fallback string) string {
	if value, exists := os.LookupEnv(key); exists {
		return value
	}
	return fallback
}

func getPostgresDSN() string {
	user := getEnv("POSTGRES_USER", "postgres")
	pass := getEnv("POSTGRES_PASSWORD", "postgres")
	db := getEnv("POSTGRES_DB", "dev_assistant")
	host := getEnv("POSTGRES_HOST", "localhost")
	port := getEnv("POSTGRES_PORT", "5432")
	return "host=" + host + " user=" + user + " password=" + pass + " dbname=" + db + " port=" + port + " sslmode=disable"
}
