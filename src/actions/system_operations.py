#!/usr/bin/env python3
"""
System Operations Module
Handles system-level actions like logout, shutdown, etc.
"""

import subprocess
import platform
import os
import logging
import sys
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SystemOperations:
    """Handles system-level operations"""
    
    @staticmethod
    def logout() -> bool:
        """
        Logout the current user
        Returns True if successful, False otherwise
        """
        try:
            system = platform.system().lower()
            logger.info(f"Attempting logout on {system}")
            
            if system == "darwin":  # macOS
                # Use AppleScript to logout on macOS
                script = 'tell application "System Events" to log out'
                result = subprocess.run(['osascript', '-e', script], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    logger.info("macOS logout command sent successfully")
                    return True
                else:
                    logger.error(f"macOS logout failed: {result.stderr}")
                    return False
                
            elif system == "linux":
                # Try common Linux logout methods
                logout_commands = [
                    ['gnome-session-quit', '--logout', '--no-prompt'],
                    ['logout'],
                    ['pkill', '-u', os.getenv('USER', os.getlogin())]
                ]
                
                for cmd in logout_commands:
                    try:
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                        if result.returncode == 0:
                            logger.info(f"Linux logout successful with command: {' '.join(cmd)}")
                            return True
                    except (subprocess.CalledProcessError, FileNotFoundError, PermissionError):
                        continue
                
                logger.error("All Linux logout methods failed")
                return False
                        
            elif system == "windows":
                # Use Windows API to logout
                result = subprocess.run(['shutdown', '/l', '/t', '0'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    logger.info("Windows logout command sent successfully")
                    return True
                else:
                    logger.error(f"Windows logout failed: {result.stderr}")
                    return False
                
            else:
                logger.error(f"Unsupported system: {system}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Logout command timed out")
            return False
        except Exception as e:
            logger.error(f"Error during logout: {e}")
            return False
    
    @staticmethod
    def lock_screen() -> bool:
        """
        Lock the screen
        Returns True if successful, False otherwise
        """
        try:
            system = platform.system().lower()
            logger.info(f"Attempting screen lock on {system}")
            
            if system == "darwin":  # macOS
                # Insist on keyboard shortcut approach with proper debugging
                
                # Method 1: Use osascript with explicit permission check
                try:
                    script = '''
                    tell application "System Events"
                        activate
                        keystroke "q" using {control down, command down}
                    end tell
                    '''
                    result = subprocess.run(['osascript', '-e', script], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        logger.info("macOS screen lock successful (Ctrl+Cmd+Q)")
                        return True
                    else:
                        logger.error(f"AppleScript failed: {result.stderr}")
                        # Check if it's a permission issue
                        if "not allowed to send keystrokes" in result.stderr:
                            logger.error("ACCESSIBILITY PERMISSION REQUIRED: Go to System Preferences > Security & Privacy > Privacy > Accessibility and add Terminal/Python")
                except (subprocess.CalledProcessError, FileNotFoundError) as e:
                    logger.error(f"AppleScript method failed: {e}")
                
                # Method 2: Use Python to directly send keystroke via pyautogui
                try:
                    import pyautogui
                    pyautogui.hotkey('ctrl', 'command', 'q')
                    logger.info("macOS screen lock successful (pyautogui)")
                    return True
                except ImportError:
                    logger.info("pyautogui not available, installing...")
                    subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyautogui'], 
                                 capture_output=True, text=True, timeout=30)
                    try:
                        import pyautogui
                        pyautogui.hotkey('ctrl', 'command', 'q')
                        logger.info("macOS screen lock successful (pyautogui after install)")
                        return True
                    except Exception as e:
                        logger.error(f"pyautogui method failed: {e}")
                except Exception as e:
                    logger.error(f"pyautogui method failed: {e}")
                
                # Method 3: Use ScreenSaverEngine as last resort
                try:
                    result = subprocess.run(['/usr/bin/open', '-a', 'ScreenSaverEngine'], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        logger.info("macOS screen lock successful (ScreenSaverEngine fallback)")
                        return True
                    else:
                        logger.error(f"ScreenSaverEngine failed: {result.stderr}")
                except Exception as e:
                    logger.error(f"ScreenSaverEngine method failed: {e}")
                
                logger.error("All macOS screen lock methods failed")
                return False
                
            elif system == "linux":
                # Try keyboard shortcuts first (Ctrl+Alt+L is common on many Linux desktops)
                try:
                    # Use xdotool to send Ctrl+Alt+L
                    result = subprocess.run(['xdotool', 'key', 'ctrl+alt+l'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        logger.info("Linux screen lock successful (Ctrl+Alt+L)")
                        return True
                except (subprocess.CalledProcessError, FileNotFoundError):
                    pass
                
                # Fallback to xdg-screensaver
                result = subprocess.run(['xdg-screensaver', 'lock'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    logger.info("Linux screen lock successful (xdg-screensaver)")
                    return True
                else:
                    logger.error(f"Linux screen lock failed: {result.stderr}")
                    return False
                
            elif system == "windows":
                # Try keyboard shortcuts first (Win+L is the standard Windows lock shortcut)
                try:
                    # Use PowerShell to send Win+L keystroke
                    ps_script = '(New-Object -ComObject WScript.Shell).SendKeys("^l")'
                    result = subprocess.run(['powershell', '-Command', ps_script], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        logger.info("Windows screen lock successful (Win+L via PowerShell)")
                        return True
                except (subprocess.CalledProcessError, FileNotFoundError):
                    pass
                
                # Fallback to rundll32 method
                result = subprocess.run(['rundll32', 'user32.dll,LockWorkStation'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    logger.info("Windows screen lock successful (rundll32)")
                    return True
                else:
                    logger.error(f"Windows screen lock failed: {result.stderr}")
                    return False
                
            else:
                logger.error(f"Unsupported system: {system}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Screen lock command timed out")
            return False
        except Exception as e:
            logger.error(f"Error during screen lock: {e}")
            return False
