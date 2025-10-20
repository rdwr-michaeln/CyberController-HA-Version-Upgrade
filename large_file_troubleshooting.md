# Large File Upload Troubleshooting Guide

## Common Issues with Large File Uploads (9GB+)

### 1. SSL EOF Errors
**Problem**: `SSLEOFError(8, 'EOF occurred in violation of protocol')`

**Causes**:
- Network instability during long uploads
- Server-side connection timeouts
- SSL handshake issues with large file transfers

**Solutions**:
- ✅ **Now Fixed**: Improved SSL handling with custom adapter
- ✅ **Now Fixed**: Chunked upload with memory management
- ✅ **Now Fixed**: Enhanced retry logic with proper error handling

### 2. Process Killed Issues
**Problem**: Process terminates with "Killed" message

**Causes**:
- Out of memory (OOM) - uploading 9GB files consumes significant RAM
- System resource limits
- Network timeouts causing system to kill the process

**Solutions**:
- ✅ **Now Fixed**: Chunked file reading (1MB chunks) to reduce memory usage
- ✅ **Now Fixed**: Garbage collection after every 500MB
- ✅ **Now Fixed**: Progress reporting to show upload is active

### 3. Connection Timeouts
**Problem**: Upload fails after several minutes

**Causes**:
- Default timeouts too short for large files
- Keep-alive not working effectively
- Network latency

**Solutions**:
- ✅ **Now Fixed**: Dynamic timeout calculation (1 hour + 1 minute per GB)
- ✅ **Now Fixed**: Improved keep-alive with 4-minute intervals
- ✅ **Now Fixed**: Better connection handling with custom HTTP adapter

## Recommendations for Large Files

### Before Starting Upload
1. **Check System Resources**:
   ```bash
   # Check available memory
   free -h
   
   # Check available disk space
   df -h .
   
   # Monitor system load
   top
   ```

2. **Network Stability**:
   - Use wired connection instead of WiFi
   - Ensure stable network during upload window
   - Consider uploading during off-peak hours

3. **System Preparation**:
   ```bash
   # Increase system limits if needed
   ulimit -n 65536
   
   # Clear system cache if low on memory
   sudo sync && sudo sysctl vm.drop_caches=3
   ```

### During Upload
- Monitor the progress indicators
- Don't interrupt the process even if it seems slow
- The upload may take 30+ minutes for 9GB files
- Keep-alive messages every 4 minutes are normal

### If Upload Still Fails
1. **Try Manual Upload via Web Interface**:
   - Access `https://controller-ip` in browser
   - Navigate to System > Software Management
   - Use the web interface for upload

2. **Split and Resume** (if supported):
   - Some systems support resumable uploads
   - Check if the server supports HTTP range requests

3. **Alternative Methods**:
   - Upload from a machine closer to the server
   - Use SCP/SFTP if server supports it
   - Contact vendor for alternative upload methods

## Recovery After Failed Upload

### Check Current State
```python
# Check if partial upload was successful
from ha_functions import login, update_status

# Login and check status
if login(base_url, username, password):
    status = update_status(base_url)
    print("Current status:", status)
```

### Resume from Checkpoint
The script automatically saves progress, so you can:
1. Restart the script
2. Choose to resume from last checkpoint
3. The script will skip completed phases

### Manual Recovery
If automation fails, follow the manual steps in `manual_recovery_guide.md`

## Performance Monitoring

### System Monitoring During Upload
```bash
# Monitor memory usage
watch -n 5 'free -h'

# Monitor network usage
watch -n 5 'netstat -i'

# Monitor disk I/O
iostat -x 5
```

### Upload Progress Indicators
- Progress percentage every 100MB
- Keep-alive messages every 4 minutes
- Memory cleanup every 500MB
- Total elapsed time display

## Contact Information
If issues persist after following this guide:
1. Check the main troubleshooting guide: `manual_recovery_guide.md`
2. Verify network connectivity and server accessibility
3. Consider using the web interface for manual upload
4. Contact your network administrator for large file transfer optimization