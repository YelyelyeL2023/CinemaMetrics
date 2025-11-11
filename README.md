# Data Visualization and Monitoring Stack

This project implements a comprehensive monitoring and visualization solution using Prometheus, Grafana, and multiple exporters to collect metrics from various sources including system metrics, database metrics, and external APIs.

## 📋 Project Overview

The stack consists of three main monitoring dashboards:

1. **Node Exporter Dashboard** - System metrics (CPU, memory, disk, network)
2. **Database Exporter Dashboard** - PostgreSQL metrics (connections, queries, cache hit ratio)
3. **Custom Exporter Dashboard** - Cryptocurrency data from CoinGecko API

## 🏗️ Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Grafana   │◄───│ Prometheus  │◄───│  Exporters  │
│   :3000     │    │   :9090     │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
                                            │
                           ┌────────────────┼────────────────┐
                           │                │                │
                    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
                    │Node Exporter│ │PG Exporter  │ │Custom Export│
                    │   :9100     │ │   :9187     │ │   :8000     │
                    └─────────────┘ └─────────────┘ └─────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- PostgreSQL database running on port 5432 (for database monitoring)
- Internet connection (for CoinGecko API access)

### 1. Clone and Start Services

```bash
# Clone the repository
git clone <repository-url>
cd DV

# Start all services
docker-compose up -d --build

# Check service status
docker-compose ps
```

### 2. Verify Services

| Service | URL | Status Check |
|---------|-----|--------------|
| Grafana | http://localhost:3000 | Login: admin/admin |
| Prometheus | http://localhost:9090 | Check Targets page |
| Custom Exporter | http://localhost:8000/metrics | Should return metrics |
| Node Exporter | http://localhost:9100/metrics | Should return metrics |
| Postgres Exporter | http://localhost:9187/metrics | Should return metrics |

### 3. Configure Grafana

1. **Access Grafana**: http://localhost:3000 (admin/admin)
2. **Add Prometheus Data Source**:
   - Go to Configuration > Data Sources
   - Add Prometheus: `http://host.docker.internal:9090`
3. **Import Dashboards**:
   - Use the provided JSON files in the repository
   - Or create custom dashboards using the PromQL queries

## 📊 Dashboard Features

### Node Exporter Dashboard
- **10+ Visualizations**: CPU usage, memory, disk I/O, network traffic
- **Visualization Types**: Gauges, time series, bar charts, stats
- **Global Variable**: `$instance` for filtering by host
- **Real-time Updates**: 10-second refresh interval

### Database Exporter Dashboard  
- **10+ Visualizations**: Connections, QPS, cache hit ratio, table statistics
- **Custom Queries**: Advanced PostgreSQL metrics via `custom_queries.yaml`
- **Global Variable**: `$instance` for database instance filtering
- **Performance Monitoring**: Query performance and resource usage

### Custom Exporter Dashboard (Cryptocurrency)
- **10+ Metrics**: Price, volume, market cap, rankings, price changes
- **External API**: Real-time data from CoinGecko API
- **Global Variable**: `$symbol` for cryptocurrency filtering
- **Update Frequency**: Every 20 seconds
- **Supported Coins**: Bitcoin, Ethereum, Dogecoin, Cardano, Litecoin

## 🔍 PromQL Queries Examples

### Custom Exporter Queries (with $symbol filter)

```promql
# Current price for selected cryptocurrency
external_coin_price_usd{symbol=~"$symbol"}

# 5-minute average price
avg_over_time(external_coin_price_usd{symbol=~"$symbol"}[5m]) by (symbol)

# Market cap ranking
1 + count(external_coin_market_cap_usd > on() group_right(symbol) external_coin_market_cap_usd{symbol=~"$symbol"}) by (symbol)

# Sum of market caps for selected symbols
sum(external_coin_market_cap_usd{symbol=~"$symbol"})

# Count cryptocurrencies with >5% 24h change
count(external_coin_price_change_24h_percent{symbol=~"$symbol"} > 5)
```

### Node Exporter Queries

```promql
# CPU usage percentage
100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle", instance="$instance"}[1m])) * 100)

# Memory usage percentage
(1 - (node_memory_MemAvailable_bytes{instance="$instance"} / node_memory_MemTotal_bytes{instance="$instance"})) * 100

# Disk I/O rate
rate(node_disk_read_bytes_total{instance="$instance"}[1m]) / 1024 / 1024
```

## 📁 Project Structure

```
DV/
├── docker-compose.yml          # Main orchestration file
├── prometheus.yml              # Prometheus configuration
├── custom_exporter.py          # Custom cryptocurrency exporter
├── Dockerfile                  # Custom exporter container
├── custom_queries.yaml         # PostgreSQL custom queries
├── grafana-data/               # Grafana persistent data
├── dashboards/
│   ├── node_exporter.json      # Node monitoring dashboard
│   ├── pg_exporter.json        # Database monitoring dashboard
│   └── crypto.json             # Cryptocurrency dashboard
└── README.md                   # This file
```

## 🔧 Configuration

### Custom Exporter Configuration

Environment variables for `custom_exporter.py`:

```bash
UPDATE_INTERVAL=20              # Update frequency in seconds
EXPORTER_PORT=8000             # Port to expose metrics
COINS=bitcoin,ethereum,dogecoin # Cryptocurrencies to monitor
```

### Prometheus Configuration

Add or modify scrape targets in `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'custom_exporter'
    scrape_interval: 15s
    static_configs:
      - targets: ['host.docker.internal:8000']
```

### Database Configuration

Update PostgreSQL connection in `docker-compose.yml`:

```yaml
environment:
  DATA_SOURCE_NAME: "postgresql://username:password@host:port/database?sslmode=disable"
```

## 🚨 Alerts Configuration

Set up alerts in Grafana for critical metrics:

- **High CPU Usage**: > 80%
- **Low Memory**: < 100MB free
- **Database Connections**: > 90% of max_connections
- **Cryptocurrency Price Changes**: > 10% in 1 hour

## 🔄 Data Collection Requirements

- **Collection Period**: 1-5 hours of continuous data
- **Update Frequencies**:
  - Node metrics: Every 15 seconds
  - Database metrics: Every 15 seconds  
  - Cryptocurrency data: Every 20 seconds
- **Data Retention**: Prometheus default (15 days)

## 🧪 Testing and Validation

### Verify Targets in Prometheus
1. Go to http://localhost:9090/targets
2. Ensure all targets show "UP" status:
   - prometheus (localhost:9090)
   - node_exporter (host.docker.internal:9100)
   - postgres_exporter (host.docker.internal:9187)
   - custom_exporter (host.docker.internal:8000)

### Test PromQL Queries
1. Go to Prometheus > Graph
2. Test sample queries from each exporter
3. Verify data is returning and updating

### Grafana Dashboard Validation
1. Import all three dashboard JSON files
2. Configure data source: http://host.docker.internal:9090
3. Test global variables (instance, symbol)
4. Verify all panels display data correctly

## 🐛 Troubleshooting

### Common Issues

**Exporter targets showing DOWN:**
```bash
# Check if services are running
docker-compose ps

# Check exporter logs
docker-compose logs custom_exporter
docker-compose logs postgres_exporter
```

**No data in Grafana:**
- Verify Prometheus data source URL
- Check time range in dashboards
- Ensure metrics are being scraped in Prometheus

**Custom exporter API errors:**
- Check internet connectivity
- Verify CoinGecko API is accessible
- Review rate limiting (60 requests/minute for free tier)

**Database connection issues:**
- Verify PostgreSQL is running and accessible
- Check connection string in docker-compose.yml
- Ensure database user has proper permissions

## 📈 Performance Optimization

- **Scrape Intervals**: Adjust based on data freshness requirements
- **Data Retention**: Configure Prometheus retention policy
- **Resource Allocation**: Monitor container resource usage
- **API Rate Limits**: Respect external API rate limits

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/new-exporter`)
3. Commit changes (`git commit -am 'Add new exporter'`)
4. Push to branch (`git push origin feature/new-exporter`)
5. Create Pull Request

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review Docker and service logs
3. Consult Prometheus and Grafana documentation
4. Open an issue in the repository

---

**Note**: This stack is designed for educational and development purposes. For production use, implement proper security measures, authentication, and monitoring best practices.