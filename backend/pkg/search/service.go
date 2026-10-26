package search

import (
	"bytes"
	"fmt"
	"io"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/shemg/developer-research-assistant/backend/pkg/common"
)

type SearchService struct {
	config *common.Config
}

func NewSearchService(cfg *common.Config) *SearchService {
	return &SearchService{
		config: cfg,
	}
}

func (s *SearchService) Start() error {
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
		c.JSON(http.StatusOK, gin.H{"status": "ok", "service": "search-service"})
	})

	// Forward endpoints directly to AI Engine
	r.POST("/api/search/query", func(c *gin.Context) {
		s.proxyToAIEngine(c, "/query")
	})

	r.POST("/api/search/diagram", func(c *gin.Context) {
		s.proxyToAIEngine(c, "/diagram")
	})

	r.POST("/api/search/refactor", func(c *gin.Context) {
		s.proxyToAIEngine(c, "/refactor")
	})

	r.POST("/api/search/architecture", func(c *gin.Context) {
		s.proxyToAIEngine(c, "/architecture")
	})

	logAddr := ":" + s.config.SearchServicePort
	return r.Run(logAddr)
}

func (s *SearchService) proxyToAIEngine(c *gin.Context, path string) {
	url := fmt.Sprintf("%s%s", s.config.AIEngineURL, path)

	bodyBytes, err := io.ReadAll(c.Request.Body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Failed to read request body: " + err.Error()})
		return
	}

	resp, err := http.Post(url, "application/json", bytes.NewBuffer(bodyBytes))
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to call AI Engine: " + err.Error()})
		return
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to read AI Engine response: " + err.Error()})
		return
	}

	c.Data(resp.StatusCode, "application/json", respBody)
}
