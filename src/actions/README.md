# System Actions for MiMi Assistant

This module provides system-level operations that can be triggered by gesture recognition.

## Available Actions

### 1. Screen Lock
- **Trigger**: Wave gesture
- **Action**: Locks the screen (does not logout - just locks)
- **Cooldown**: 5 seconds between attempts to prevent multiple triggers
- **Platform Support**: 
  - macOS: Uses AppleScript to send Ctrl+Cmd+Q (default lock screen shortcut)
  - Linux: Uses xdotool to send Ctrl+Alt+L (common lock screen shortcut)
  - Windows: Uses PowerShell to send Win+L (standard lock screen shortcut)

### 2. Logout
- **Trigger**: (Not currently mapped to a gesture)
- **Action**: Logs out the current user from the system
- **Platform Support**: 
  - macOS: Uses AppleScript
  - Linux: Tries multiple methods (gnome-session-quit, logout, pkill)
  - Windows: Uses shutdown command

## Configuration

The wave-to-screen-lock functionality is currently hardcoded in `camera_app.py`. To modify:

1. **Change the action**: Edit the `trigger_waving_action` function in `src/camera/camera_app.py`
2. **Adjust cooldown**: Modify `lock_cooldown_s` variable in `src/camera/camera_app.py`
3. **Add new gestures**: Extend the gesture recognition logic and map to different system operations

## Usage

1. Start MiMi Assistant: `python src/main.py`
2. Say "Hey Mycroft" to activate the camera
3. Wave at the camera to lock the screen
4. The screen will be locked immediately (you'll need to unlock with your password/biometrics)

## Permissions

### macOS
- The application may need accessibility permissions to perform logout
- Grant permissions in System Preferences > Security & Privacy > Privacy > Accessibility

### Linux
- May require appropriate permissions to kill user sessions
- Test with your specific desktop environment

### Windows
- Should work with standard user permissions
- Administrator rights not required for logout

## Safety Features

- **Cooldown Period**: 5-second cooldown prevents accidental multiple logouts
- **Error Handling**: Graceful failure with informative messages
- **Cross-Platform**: Automatically detects and uses appropriate system commands
- **Logging**: Detailed logging for debugging (check console output)

## Troubleshooting

### Screen lock not working:
1. **macOS Accessibility Permissions**: 
   - Go to System Preferences > Security & Privacy > Privacy > Accessibility
   - Add Terminal or Python to the allowed applications
   - This is required for keyboard shortcut automation

2. **Camera Issues**:
   - Check if camera is being used by another application (Zoom, FaceTime, etc.)
   - Grant camera permissions in System Preferences > Security & Privacy > Privacy > Camera
   - Try different camera indices if default (0) doesn't work

3. **Test commands manually**:
   - macOS: `osascript -e 'tell application "System Events" to keystroke "q" using {control down, command down}'` (Ctrl+Cmd+Q)
   - Linux: `xdotool key ctrl+alt+l` (Ctrl+Alt+L) or `xdg-screensaver lock` (fallback)
   - Windows: `powershell -Command "(New-Object -ComObject WScript.Shell).SendKeys(\"^l\")"` (Win+L)

### False positives:
1. Adjust wave detection parameters in `camera_app.py`:
   - `min_wave_amplitude`: Minimum movement required
   - `min_crossings`: Number of direction changes required
   - `min_speed`: Minimum speed threshold

### Cooldown too long/short:
1. Modify `lock_cooldown_s` in `camera_app.py`
2. Set to 0 to disable cooldown (not recommended)

## Future Enhancements

- Configuration file for mapping gestures to actions
- GUI for configuring actions
- More system operations (shutdown, restart, etc.)
- Custom actions support
- Gesture-specific configurations
