package user

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/shemg/developer-research-assistant/backend/pkg/common"
)

type User struct {
	ID    string `json:"id"`
	Email string `json:"email"`
	Name  string `json:"name"`
}

type UserService struct {
	config *common.Config
	users  map[string]User
}

func NewUserService(cfg *common.Config) *UserService {
	// Initialize with mock users
	mockUsers := map[string]User{
		"1": {ID: "1", Email: "shem@example.com", Name: "Shem Gikunda"},
	}
	return &UserService{
		config: cfg,
		users:  mockUsers,
	}
}

func (s *UserService) Start() error {
	r := gin.Default()
	
	// CORS configurations
	r.Use(func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
		c.Writer.Header().Set("Access-Control-Allow-Credentials", "true")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, Content-Length, Accept-Encoding, X-CSRF-Token, Authorization, accept, origin, Cache-Control, X-Requested-With")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "POST, OPTIONS, GET, PUT, DELETE")
		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}
		c.Next()
	})

	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok", "service": "user-service"})
	})

	r.POST("/api/users/login", func(c *gin.Context) {
		var req struct {
			Email    string `json:"email"`
			Password string `json:"password"`
		}
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		// Accept any password for mock login
		user, exists := s.findUserByEmail(req.Email)
		if !exists {
			// Auto register
			user = User{
				ID:    "user_" + common.RandomString(6),
				Email: req.Email,
				Name:  "Developer User",
			}
			s.users[user.ID] = user
		}

		c.JSON(http.StatusOK, gin.H{
			"token": "mock_jwt_token_" + user.ID,
			"user":  user,
		})
	})

	r.GET("/api/users/profile", func(c *gin.Context) {
		// Mock auth extraction
		token := c.GetHeader("Authorization")
		if token == "" {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Unauthorized"})
			return
		}
		
		c.JSON(http.StatusOK, s.users["1"]) // Default to first user for prototype
	})

	logAddr := ":" + s.config.UserServicePort
	return r.Run(logAddr)
}

func (s *UserService) findUserByEmail(email string) (User, bool) {
	for _, u := range s.users {
		if u.Email == email {
			return u, true
		}
	}
	return User{}, false
}
