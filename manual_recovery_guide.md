# Manual Recovery Guide for HA Automation Script

This guide provides step-by-step manual recovery procedures when the automation script encounters errors or fails to complete.

## 🚨 Emergency Recovery Procedures

### 1. Script Stops During HA Disable (Phase 2)

**Symptoms:**
- Script stuck on "Waiting for HA to be disabled"
- HA status shows "disabling" for extended period
- Connection errors to primary server

**Manual Recovery Steps:**

#### Option A: Force HA Disable 

1. Login to primary server web interface
2. Navigate to: High Availability
3. Click "Disable HA" button
4. Check "Force" option if available
5. Confirm the action


### 2. Script Fails During Version Update (Phase 3-4)

**Symptoms:**
- Upload fails or times out
- Server becomes unresponsive
- Update status shows error

**Manual Recovery Steps:**

#### Option A: Manual Upload via Web Interface
1. Login to server web interface
2. Navigate to: System → Software Management
3. Click "Upload" and select your upgrade file
4. Wait for upload completion
5. Click "Install" to commit the update

#### Option B: Resume Using Checkpoints
1. Check the `checkpoint.json` file in your project directory
2. Verify the last completed phase in the checkpoint
3. Run the main script again - it will automatically detect the checkpoint
4. Choose to resume from the last successful phase when prompted

#### Option C: Manual Checkpoint Recovery
1. If checkpoint is corrupted, check `checkpoint_archive_*.json` files
2. Copy a valid checkpoint back to `checkpoint.json`
3. Edit the checkpoint file to mark Phase 3 as incomplete:
   ```json
   {
     "current_phase": 2,
     "completed_phases": [1, 2],
     "phase_3_upload": false
   }
   ```
4. Resume the script

### 3. Script Fails During Config Migration (Phase 5)

**Symptoms:**
- Config download fails
- Upload to secondary fails
- Invalid license prevents migration

**Manual Recovery Steps:**

#### Option A: Manual Config Export/Import
1. **Export from Primary:**
   - Login to primary web interface
   - Navigate to: Configuration → Export/Import
   - Select "DefenseFlow Configuration"
   - Download the config file

2. **Import to Secondary:**
   - Login to secondary web interface
   - Navigate to: Configuration → Export/Import
   - Upload the downloaded config file
   - Apply the configuration

#### Option B: Resume Using Checkpoints
1. Check your checkpoint status in `checkpoint.json`
2. If Phase 5 is marked as failed, you can skip it:
   ```json
   {
     "current_phase": 5,
     "skip_config_migration": true,
     "reason": "License incompatibility"
   }
   ```
3. Resume the script - it will skip config migration and proceed to HA establishment

### 4. Script Fails During HA Re-establishment (Phase 6-7)

**Symptoms:**
- HA establishment fails
- Nodes don't sync properly


**Manual Recovery Steps:**

#### Option A: Resume Using Checkpoints
1. Stop the current script execution
2. Check the `checkpoint.json` file to see the current state
3. If HA establishment is failing, reset the checkpoint:
   ```json
   {
     "current_phase": 6,
     "ha_establishment_attempts": 0,
     "force_ha_reset": true
   }
   ```
4. Resume the script - it will attempt HA establishment with reset

#### Option B: Via Web Interface
1. Login to primary server
2. Navigate to: System → High Availability
3. Fill in:
   - Primary IP: `<primary_ip>`
   - Secondary IP: `<secondary_ip>`
   - Secondary credentials
4. Enable auto-failover
5. Click "Establish HA"
6. Update checkpoint manually to reflect completion:
   ```json
   {
     "current_phase": 7,
     "completed_phases": [1, 2, 3, 4, 5, 6],
     "ha_established": true
   }
   ```

#### Option C: Checkpoint Reset and Restart
1. If HA is in bad state, update the checkpoint to force reset:
   ```json
   {
     "current_phase": 6,
     "force_ha_disable": true,
     "ha_reset_required": true
   }
   ```
2. Resume the script - it will disable HA first, then re-establish

## 🔍 Troubleshooting Commands

### Check Checkpoint Status
```bash
# View current checkpoint
cat checkpoint.json

# View checkpoint history
ls -la checkpoint_archive_*.json

# View latest archived checkpoint
cat $(ls -t checkpoint_archive_*.json | head -1)
```

### Check System Status via Web Interface
- Login to server web interface
- Navigate to: System → Status
- Check system health and connectivity
- Verify HA status in High Availability section

### Check Version Status via Web Interface
- Login to server web interface  
- Navigate to: System → Software Management
- View current version and update status
- Check for any pending installations

## 📋 Recovery Checklist

When script fails, follow this checklist:

### Immediate Actions
- [ ] Note the exact error message
- [ ] Check which phase failed in `checkpoint.json`
- [ ] Verify server connectivity via web interface
- [ ] Check system logs in web interface

### Assessment
- [ ] Determine if rollback is needed
- [ ] Check data integrity
- [ ] Verify HA state
- [ ] Assess impact on production

### Recovery
- [ ] Choose appropriate recovery method
- [ ] Execute recovery steps
- [ ] Verify system functionality
- [ ] Document the incident

### Post-Recovery
- [ ] Test all critical functions
- [ ] Monitor system stability
- [ ] Update recovery procedures
- [ ] Plan prevention measures

## 🚨 Emergency Contacts

When manual recovery is needed:

1. **System Administrator**: Contact your network admin
2. **Vendor Support**: Contact Radware support if needed
3. **Escalation**: Follow your organization's escalation procedures

## 📝 Recovery Logging

The script automatically logs recovery actions in checkpoints

## 🔄 Resume Script After Manual Recovery

The script uses checkpoints to automatically resume after manual intervention:

### Automatic Resume
1. **Run the script normally**: `python3 main.py`
2. **Script detects checkpoint**: Automatically offers to resume
3. **Choose resume option**: Script continues from last successful phase
4. **Monitor progress**: Script updates checkpoint as it progresses

### Manual Checkpoint Editing
If you need to manually adjust the checkpoint:

```json
{
  "current_phase": 4,
  "completed_phases": [1, 2, 3],
  "timestamp": "2025-07-23T10:30:00",
  "primary_ip": "192.168.1.10",
  "secondary_ip": "192.168.1.11",
  "manual_intervention": true,
  "notes": "Phase 3 completed manually via web interface"
}
```

### Checkpoint Recovery Scenarios
- **Corrupted checkpoint**: Copy from `checkpoint_archive_*.json`
- **Skip failed phase**: Mark phase as completed in checkpoint
- **Force retry**: Reset phase status in checkpoint
- **Clean start**: Delete `checkpoint.json` to start fresh

Remember: Always test the recovery procedures in a non-production environment first!
