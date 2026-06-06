# AXON UI Control Panel

## Overview

The UI Control Panel provides a graphical interface for managing and running the AXON pipeline. It allows users to configure domains, lenses, and processing options without needing command-line tools.

## Features

### Domain Management
- **Domain Selection**: Choose from available research domains (construction science, biohacking longevity, etc.)
- **Domain Information**: View domain descriptions and configuration details
- **Domain-Specific Processing**: Automatically applies domain-specific rules and filters

### Lens Configuration
- **Lens Selection**: Select multiple lenses to apply during processing
- **Lens Preview**: View available lenses and their purposes
- **Multi-Lens Support**: Combine multiple analytical perspectives

### Processing Controls
- **PDF Processing**: Run the main scraper on PDF documents
- **RSS Ingestion**: Process RSS feeds for new content
- **Results Export**: Run dual-lens export for the selected domain
- **Progress Monitoring**: Real-time progress bars and status updates

### Configuration Management
- **Input/Output Paths**: Configure directories for PDFs and databases
- **Database Management**: Select and manage SQLite database files
- **System Status**: Check system health and configuration

## Installation

### Prerequisites
- Python 3.10 or higher
- Existing AXON repository checkout

### Dependencies
The UI works with Python's standard library modules:
- `tkinter` - GUI framework (included with Python)
- `json` - Configuration file handling
- `os`, `sys`, `subprocess` - System operations
- `threading` - Background processing
- `logging` - Application logging

Optional external packages (listed in requirements_ui.txt):
- `ttkbootstrap>=1.8.0` - For theming and bootstrap-styled widgets (enhancement)
- `plyer>=2.1.0` - For cross-platform notifications (enhancement)

Note: The UI will function with just the standard library, but these packages provide optional visual and notification improvements.

## Usage

### Launching the UI
```bash
python ui_control_panel.py
```

### Basic Workflow

1. **Configure Domain**
   - Select your research domain from the dropdown
   - The UI will automatically load domain-specific settings

2. **Select Lenses**
   - Choose which analytical lenses to apply
   - Multiple lenses can be selected for comprehensive analysis

3. **Set Paths**
   - Configure input directory containing PDF files
   - Set output database path
   - Use browse buttons to navigate file system

4. **Run Processing**
   - Click "Run Scraper" to process PDFs
   - Monitor progress with real-time updates
   - View results in the output panel

5. **Export Results**
   - Use "Export Results" to generate reports
   - Save output to text files for further analysis

### Advanced Features

#### RSS Feed Processing
- Configure RSS feeds in `config/feeds.json`
- Use "Run RSS Ingest" to process new content
- Automatically downloads and processes PDFs from feeds

#### Status Monitoring
- Check system status with "Check Status" button
- View loaded domains, lenses, and configuration
- Monitor input directory and database status

#### Output Management
- Real-time output display in scrollable text area
- Clear output with "Clear Output" button
- Save output to files with "Save Output" button

## Configuration Files

### Domain Configuration
Domains are loaded from `config/domains/` first, with `seeds/domains/` as a legacy fallback:
- Each domain has a JSON configuration file
- Defines domain-specific rules and preferences
- Controls pattern emphasis and entity types

### Lens Configuration
Lenses are loaded from `lenses/` directory:
- Python files with `_v1.py` naming convention
- Define analytical patterns and rules
- Applied during PDF processing

### RSS Feeds
RSS feeds configured in `config/feeds.json`:
```json
{
  "feeds": [
    {
      "name": "Feed Name",
      "url": "http://example.com/rss",
      "domain": "domain_id",
      "enabled": true
    }
  ]
}
```

## Troubleshooting

### Common Issues

#### "Domain not found"
- Ensure domain JSON files exist in `config/domains/` (or `seeds/domains/` for legacy setups)
- Check file format and required fields
- Verify domain ID matches configuration

#### "Lenses not loading"
- Check `lenses/` directory exists
- Ensure lens files follow `_v1.py` naming convention
- Verify Python syntax in lens files

#### "Database not found"
- Create parent directories if they don't exist
- Check file permissions for database directory
- Use "Browse" button to select valid database path

#### "Input directory not found"
- Create input directory if it doesn't exist
- Ensure directory contains PDF files
- Check file permissions

### Error Messages

The UI provides detailed error messages for:
- Missing configuration files
- Invalid file paths
- Processing errors
- System status issues

## Performance Tips

### Large PDF Collections
- Process PDFs in smaller batches
- Monitor system memory usage
- Use progress indicators to track processing

### Database Performance
- Regularly backup database files
- Consider database optimization for large datasets
- Monitor disk space for output files

### RSS Processing
- Configure feed update frequency appropriately
- Monitor network connectivity for feed downloads
- Set reasonable timeout values for large files

## Security Considerations

### File Access
- The UI only accesses files in specified directories
- No external network access except for RSS feeds
- Database files are stored locally

### Input Validation
- All file paths are validated before processing
- Configuration files are parsed safely
- Error handling prevents system crashes

## Development

### Adding New Domains
1. Create JSON configuration in `config/domains/`
2. Define domain ID, name, and rules
3. Restart UI to load new domain

### Adding New Lenses
1. Create Python file in `lenses/` directory
2. Follow existing lens file patterns
3. Use `_v1.py` naming convention
4. Restart UI to load new lens

### Customizing UI
- Modify `ui_control_panel.py` for layout changes
- Add new buttons and controls as needed
- Update event handlers for new functionality

## Integration

### Command Line Integration
The UI can be used alongside command-line tools:
- Use CLI for batch processing
- Use UI for interactive configuration
- Share configuration files between interfaces

### Script Integration
- UI configuration files are JSON format
- Can be read by other Python scripts
- Compatible with existing processing pipeline

## Support

For issues or questions:
1. Check this README for common solutions
2. Review error messages in the output panel
3. Verify configuration files are properly formatted
4. Ensure all required directories exist

The UI is designed to be user-friendly and self-documenting. Most operations include helpful tooltips and status messages.