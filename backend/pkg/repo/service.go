package repo

import (
	"archive/zip"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/shemg/developer-research-assistant/backend/pkg/common"
)

type Repository struct {
	ID        string    `json:"id"`
	Name      string    `json:"name"`
	Path      string    `json:"path"`
	Type      string    `json:"type"` // "zip" or "local"
	Status    string    `json:"status"` // "indexing", "ready", "failed"
	CreatedAt time.Time `json:"created_at"`
}

type RepoService struct {
	config    *common.Config
	repos     map[string]*Repository
	reposLock sync.RWMutex
}

func NewRepoService(cfg *common.Config) *RepoService {
	return &RepoService{
		config: cfg,
		repos:  make(map[string]*Repository),
	}
}

func (s *RepoService) Start() error {
	r := gin.Default()
	
	// Ensure uploads directory exists
	os.MkdirAll("./repos", 0755)

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
		c.JSON(http.StatusOK, gin.H{"status": "ok", "service": "repo-service"})
	})

	r.GET("/api/repos", func(c *gin.Context) {
		s.reposLock.RLock()
		list := make([]Repository, 0, len(s.repos))
		for _, repo := range s.repos {
			list = append(list, *repo)
		}
		s.reposLock.RUnlock()
		c.JSON(http.StatusOK, list)
	})

	r.POST("/api/repos/index-local", func(c *gin.Context) {
		var req struct {
			Path string `json:"path"`
		}
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		if _, err := os.Stat(req.Path); os.IsNotExist(err) {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Provided local directory path does not exist"})
			return
		}

		repoID := "repo_" + common.RandomString(6)
		repoName := filepath.Base(req.Path)
		repo := &Repository{
			ID:        repoID,
			Name:      repoName,
			Path:      req.Path,
			Type:      "local",
			Status:    "indexing",
			CreatedAt: time.Now(),
		}

		s.reposLock.Lock()
		s.repos[repoID] = repo
		s.reposLock.Unlock()

		// Trigger indexing in background
		go s.indexCodebase(repo)

		c.JSON(http.StatusOK, repo)
	})

	r.POST("/api/repos/upload", func(c *gin.Context) {
		file, header, err := c.Request.FormFile("file")
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Failed to read file from form: " + err.Error()})
			return
		}
		defer file.Close()

		repoID := "repo_" + common.RandomString(6)
		repoName := strings.TrimSuffix(header.Filename, filepath.Ext(header.Filename))
		destDir := filepath.Join(".", "repos", repoID)

		// Unzip file
		err = s.unzipFile(file, header.Size, destDir)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to unzip repository: " + err.Error()})
			return
		}

		// Absolute path for indexing
		absPath, _ := filepath.Abs(destDir)

		repo := &Repository{
			ID:        repoID,
			Name:      repoName,
			Path:      absPath,
			Type:      "zip",
			Status:    "indexing",
			CreatedAt: time.Now(),
		}

		s.reposLock.Lock()
		s.repos[repoID] = repo
		s.reposLock.Unlock()

		// Trigger indexing in background
		go s.indexCodebase(repo)

		c.JSON(http.StatusOK, repo)
	})

	logAddr := ":" + s.config.RepoServicePort
	return r.Run(logAddr)
}

func (s *RepoService) unzipFile(file io.ReaderAt, size int64, dest string) error {
	reader, err := zip.NewReader(file, size)
	if err != nil {
		return err
	}

	for _, f := range reader.File {
		fpath := filepath.Join(dest, f.Name)

		// Check for Zip Slip vulnerability
		if !strings.HasPrefix(fpath, filepath.Clean(dest)+string(filepath.Separator)) {
			return fmt.Errorf("illegal file path: %s", fpath)
		}

		if f.FileInfo().IsDir() {
			os.MkdirAll(fpath, os.ModePerm)
			continue
		}

		if err = os.MkdirAll(filepath.Dir(fpath), os.ModePerm); err != nil {
			return err
		}

		outFile, err := os.OpenFile(fpath, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, f.Mode())
		if err != nil {
			return err
		}

		rc, err := f.Open()
		if err != nil {
			outFile.Close()
			return err
		}

		_, err = io.Copy(outFile, rc)
		outFile.Close()
		rc.Close()

		if err != nil {
			return err
		}
	}
	return nil
}

func (s *RepoService) indexCodebase(repo *Repository) {
	// Call Python AI Engine to chunk and embed codebase
	url := fmt.Sprintf("%s/index", s.config.AIEngineURL)
	
	reqBody, _ := json.Marshal(map[string]interface{}{
		"directory_path": repo.Path,
	})

	resp, err := http.Post(url, "application/json", bytes.NewBuffer(reqBody))
	if err != nil {
		fmt.Printf("[RepoService] Error requesting AI engine: %v\n", err)
		s.updateRepoStatus(repo.ID, "failed")
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		var errData map[string]interface{}
		_ = json.NewDecoder(resp.Body).Decode(&errData)
		fmt.Printf("[RepoService] AI engine indexing failed: %v\n", errData)
		s.updateRepoStatus(repo.ID, "failed")
		return
	}

	s.updateRepoStatus(repo.ID, "ready")
	fmt.Printf("[RepoService] Repository %s (%s) indexing complete.\n", repo.Name, repo.ID)
}

func (s *RepoService) updateRepoStatus(id, status string) {
	s.reposLock.Lock()
	defer s.reposLock.Unlock()
	if r, ok := s.repos[id]; ok {
		r.Status = status
	}
}
