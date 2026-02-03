# xndctl - X News Digest CLI Tool

A command-line interface for managing the X News Digest system. Provides user-friendly commands for CRUD operations on users, topics, subscriptions, and manual triggering of data collection and digest notifications.

## Features

- **User Management**: Create, list, update, and delete users
- **Topic Management**: Create, list, update, and delete topics with cron-based scheduling
- **Subscription Management**: Create, list, and delete subscriptions linking users to topics
- **Manual Triggers**: Manually trigger topic data collection
- **Digest Notifications**: Manually send digest notifications to subscriptions
- **Multiple Output Formats**: table (default), JSON, and YAML
- **Interactive Prompts**: User-friendly interactive mode for all operations
- **Configuration Management**: Persistent configuration with YAML

## Installation

### From Source

```bash
cd cli/
pip install -e .
```

### Requirements

- Python 3.10+
- X News Digest backend API running

## Quick Start

1. **Initialize Configuration**

On first run, xndctl will automatically prompt you to configure the API connection:

```bash
xndctl config
```

Or manually initialize:

```bash
xndctl init
```

2. **Create a User**

```bash
# Interactive mode (recommended)
xndctl user create -p

# Flag-based mode
xndctl user create --name "John Doe" --email "john@example.com"
```

3. **Create a Topic**

```bash
# Interactive mode with cron validation
xndctl topic create -p

# Flag-based mode
xndctl topic create --name "AI News" --query "artificial intelligence" --cron "0 8 * * *"
```

4. **Create a Subscription**

```bash
# Interactive mode (required for subscriptions)
xndctl sub create -p
```

5. **Trigger Topic Collection**

```bash
xndctl trigger -p
```

6. **Send Digest Notification**

```bash
xndctl notify -p
```

## Configuration

Configuration is stored at `~/.xndctl/config.yaml`:

```yaml
api:
  base_url: "http://localhost:8000"
  timeout: 30
  verify_ssl: true

output:
  default_format: "table"
  color: true

logging:
  level: "INFO"
```

### View Current Configuration

```bash
xndctl config
```

### Reinitialize Configuration

```bash
xndctl init
```

## Commands

### Global Options

- `--verbose, -v`: Enable verbose error output
- `--output, -o [table|json|yaml]`: Output format

### User Commands

#### Create User

```bash
# Interactive mode
xndctl user create -p

# Flag-based mode
xndctl user create --name "John Doe" --email "john@example.com" \
  --feishu-webhook-url "https://..." \
  --feishu-webhook-secret "secret"
```

#### List Users

```bash
xndctl user ls
xndctl user ls --limit 50 --offset 0
xndctl user ls --output json
```

#### Get User Details

```bash
xndctl user get --id <uuid>
xndctl user get --name "John Doe"
xndctl user get --email "john@example.com"
```

#### Update User

```bash
# Interactive mode
xndctl user update --name "John Doe" -p

# Flag-based mode
xndctl user update --name "John Doe" --new-email "newemail@example.com"
```

#### Delete User

```bash
xndctl user delete --name "John Doe"
xndctl user delete --id <uuid> -y  # Skip confirmation
```

### Topic Commands

#### Create Topic

```bash
# Interactive mode with cron validation
xndctl topic create -p

# Flag-based mode
xndctl topic create --name "AI News" --query "artificial intelligence" --cron "0 8 * * *"
```

**Cron Expression Format**: `minute hour day month weekday`

Examples:
- `0 8 * * *` - Daily at 8:00 AM
- `0 */6 * * *` - Every 6 hours
- `0 9 * * 1` - Every Monday at 9:00 AM

#### List Topics

```bash
xndctl topic ls
xndctl topic ls --limit 50 --offset 0
```

#### Get Topic Details

```bash
xndctl topic get --name "AI News"
xndctl topic get --id <uuid>
```

#### Update Topic

```bash
# Interactive mode
xndctl topic update --name "AI News" -p

# Flag-based mode
xndctl topic update --name "AI News" --new-name "AI & ML News" --cron "0 9 * * *"
xndctl topic update --name "AI News" --enable
xndctl topic update --name "AI News" --disable
```

#### Delete Topic

```bash
xndctl topic delete --name "AI News"
xndctl topic delete --id <uuid> -y  # Skip confirmation
```

### Subscription Commands

#### Create Subscription

```bash
# Interactive mode (required)
xndctl sub create -p
```

This will:
1. Show list of available users
2. Show list of available topics
3. Prompt for notification channel selection (Feishu, Email)
4. Confirm before creating

#### List Subscriptions

```bash
xndctl sub ls
xndctl sub ls --user-id <uuid>
xndctl sub ls --topic-id <uuid>
```

#### Get Subscription Details

```bash
xndctl sub get --id <uuid>
```

#### Delete Subscription

```bash
xndctl sub delete --id <uuid>
xndctl sub delete --id <uuid> -y  # Skip confirmation
```

### Trigger Commands

#### Trigger Topic Collection

```bash
xndctl trigger -p
```

This will:
1. Show list of available topics
2. Trigger collection for selected topic
3. Display task ID for tracking

### Notify Commands

#### Send Digest Notification

```bash
xndctl notify -p
```

This will:
1. Show list of recent digests
2. Show subscriptions for selected digest's topic
3. Send notification to selected subscription
4. Display delivery statistics (success/failure counts)

## Output Formats

### Table (Default)

Human-readable table format with pagination metadata:

```bash
xndctl user ls
```

### JSON

Machine-readable JSON format:

```bash
xndctl user ls --output json
xndctl user ls -o json
```

### YAML

Human-readable YAML format:

```bash
xndctl topic ls --output yaml
```

## Error Handling

### Non-Verbose Mode (Default)

Clean error messages:

```bash
xndctl user delete --name "NonExistent"
# Error: User with name 'NonExistent' not found
```

### Verbose Mode

Detailed error information with traceback:

```bash
xndctl user ls --verbose
xndctl user ls -v
```

## Examples

### Complete Workflow

```bash
# 1. Create a user
xndctl user create -p
# Name: John Doe
# Email: john@example.com

# 2. Create a topic
xndctl topic create -p
# Name: AI News
# Query: artificial intelligence
# Cron: 0 8 * * *

# 3. Create a subscription
xndctl sub create -p
# Select user: 1 (John Doe)
# Select topic: 1 (AI News)
# Enable Feishu: Yes
# Enable Email: Yes

# 4. Trigger collection
xndctl trigger -p
# Select topic: 1 (AI News)

# 5. Send notification (after collection completes)
xndctl notify -p
# Select digest: 1
# Select subscription: 1
```

### Batch Operations

```bash
# Create multiple users from a script
for email in user1@example.com user2@example.com; do
  xndctl user create --email "$email" --name "$email"
done

# List all subscriptions in JSON for processing
xndctl sub ls --output json | jq '.items[] | {user: .user.email, topic: .topic.name}'
```

## Troubleshooting

### Cannot connect to API

```bash
# Check API URL in configuration
xndctl config

# Update API URL
xndctl init
```

### Invalid cron expression

Use the format: `minute hour day month weekday`

Valid examples:
- `0 8 * * *` (daily at 8 AM)
- `*/30 * * * *` (every 30 minutes)
- `0 0 * * 0` (weekly on Sunday at midnight)

Test at: https://crontab.guru

### Permission errors

Ensure the backend API is running and accessible:

```bash
curl http://localhost:8000/health
```

## Development

### Install for Development

```bash
cd cli/
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest tests/
```

### Project Structure

```
cli/
├── xndctl/
│   ├── __init__.py
│   ├── cli.py              # Main CLI entry point
│   ├── config.py           # Configuration management
│   ├── client.py           # API client
│   ├── schemas.py          # Pydantic models
│   ├── utils.py            # Display & error handling
│   ├── commands/           # Command implementations
│   │   ├── user.py
│   │   ├── topic.py
│   │   ├── subscription.py
│   │   ├── trigger.py
│   │   └── notify.py
│   └── prompts/            # Interactive prompts
│       ├── user.py
│       ├── topic.py
│       └── subscription.py
├── tests/
├── setup.py
└── README.md
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License
