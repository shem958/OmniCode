package gateway

import (
	"fmt"
	"net/http"
	"net/http/httputil"
	"net/url"

	"github.com/gin-gonic/gin"
	"github.com/shemg/developer-research-assistant/backend/pkg/common"
)

type GatewayService struct {
	config *common.Config
}

func NewGatewayService(cfg *common.Config) *GatewayService {
	return &GatewayService{
		config: cfg,
	}
}

func (g *GatewayService) Start() error {
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
		c.JSON(http.StatusOK, gin.H{
			"status": "ok",
			"service": "api-gateway",
			"routing": gin.H{
				"user_service":   ":" + g.config.UserServicePort,
				"repo_service":   ":" + g.config.RepoServicePort,
				"search_service": ":" + g.config.SearchServicePort,
			},
		})
	})

	// Setup Reverse Proxies for the services
	userProxy := newProxy("http://localhost:" + g.config.UserServicePort)
	repoProxy := newProxy("http://localhost:" + g.config.RepoServicePort)
	searchProxy := newProxy("http://localhost:" + g.config.SearchServicePort)

	// Route traffic
	r.Any("/api/users/*any", func(c *gin.Context) {
		userProxy.ServeHTTP(c.Writer, c.Request)
	})
	r.Any("/api/users", func(c *gin.Context) {
		userProxy.ServeHTTP(c.Writer, c.Request)
	})

	r.Any("/api/repos/*any", func(c *gin.Context) {
		repoProxy.ServeHTTP(c.Writer, c.Request)
	})
	r.Any("/api/repos", func(c *gin.Context) {
		repoProxy.ServeHTTP(c.Writer, c.Request)
	})

	r.Any("/api/search/*any", func(c *gin.Context) {
		searchProxy.ServeHTTP(c.Writer, c.Request)
	})
	r.Any("/api/search", func(c *gin.Context) {
		searchProxy.ServeHTTP(c.Writer, c.Request)
	})

	logAddr := ":" + g.config.GatewayPort
	fmt.Printf("[Gateway] API Gateway starting on port %s\n", g.config.GatewayPort)
	return r.Run(logAddr)
}

func newProxy(target string) *httputil.ReverseProxy {
	urlTarget, err := url.Parse(target)
	if err != nil {
		panic(err)
	}
	proxy := httputil.NewSingleHostReverseProxy(urlTarget)
	
	// Adjust request host for target service
	originalDirector := proxy.Director
	proxy.Director = func(req *http.Request) {
		originalDirector(req)
		req.Host = urlTarget.Host
		
		// Ensure headers flow correctly
		if _, ok := req.Header["User-Agent"]; !ok {
			req.Header.Set("User-Agent", "Developer-Research-Assistant-Gateway")
		}
	}

	// Clean up duplicate CORS headers returned by target services to prevent browser blocks
	proxy.ModifyResponse = func(resp *http.Response) error {
		resp.Header.Del("Access-Control-Allow-Origin")
		resp.Header.Del("Access-Control-Allow-Credentials")
		resp.Header.Del("Access-Control-Allow-Headers")
		resp.Header.Del("Access-Control-Allow-Methods")
		return nil
	}

	return proxy
}
