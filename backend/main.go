package main

import (
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/shemg/developer-research-assistant/backend/pkg/common"
	"github.com/shemg/developer-research-assistant/backend/pkg/gateway"
	"github.com/shemg/developer-research-assistant/backend/pkg/repo"
	"github.com/shemg/developer-research-assistant/backend/pkg/search"
	"github.com/shemg/developer-research-assistant/backend/pkg/user"
)

func main() {
	serviceFlag := flag.String("service", "all", "Specify service to run: all, gateway, user, repo, search")
	flag.Parse()

	cfg := common.LoadConfig()

	// Handle graceful shutdown
	errChan := make(chan error, 5)
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	runService := func(name string, startFunc func() error) {
		go func() {
			fmt.Printf("[%s] starting...\n", name)
			if err := startFunc(); err != nil {
				fmt.Printf("[%s] error: %v\n", name, err)
				errChan <- err
			}
		}()
	}

	if *serviceFlag == "all" || *serviceFlag == "user" {
		uSvc := user.NewUserService(cfg)
		runService("UserService", uSvc.Start)
	}

	if *serviceFlag == "all" || *serviceFlag == "repo" {
		rSvc := repo.NewRepoService(cfg)
		runService("RepoService", rSvc.Start)
	}

	if *serviceFlag == "all" || *serviceFlag == "search" {
		sSvc := search.NewSearchService(cfg)
		runService("SearchService", sSvc.Start)
	}

	// Sleep slightly to let subservices start before gateway
	if *serviceFlag == "all" || *serviceFlag == "gateway" {
		gSvc := gateway.NewGatewayService(cfg)
		runService("GatewayService", gSvc.Start)
	}

	select {
	case err := <-errChan:
		log.Fatalf("Fatal service error: %v", err)
	case sig := <-sigChan:
		fmt.Printf("Received signal %v, shutting down...\n", sig)
	}
}
