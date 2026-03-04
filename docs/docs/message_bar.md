# MessageBar

The `MessageBar` widget provides a user-friendly way to display notifications, warnings, and error messages in your Qt application.

## Features

- **Three severity levels**: Success (green), Warning (yellow), and Error (red)
- **Auto-dismissal**: Success messages automatically disappear after 5 seconds with a countdown indicator
- **Manual dismissal**: Warning and error messages stay until explicitly closed
- **Exception details**: Error messages can include a "Details" button showing full tracebacks
- **QGIS integration**: Automatically uses `QgsMessageBar` when running inside QGIS
- **Scrollable**: Multiple messages stack and become scrollable when needed

## Basic Usage

```python
from pgserviceparser.gui import MessageBar, MessageLevel

# Create the message bar
message_bar = MessageBar()
layout.addWidget(message_bar)

# Display different types of messages
message_bar.pushSuccess("Operation completed successfully")
message_bar.pushWarning("Please review the configuration")
message_bar.pushError("Failed to save file")
```

## With Exception Details

When an error occurs, you can attach the exception object to show a "Details" button:

```python
try:
    risky_operation()
except Exception as e:
    message_bar.pushError("Operation failed", exception=e)
```

Users can click the "Details" button to view the full traceback in a dialog.

## Using Custom Severity Levels

```python
from pgserviceparser.gui import MessageBar, MessageLevel

# Use pushMessage with explicit level
message_bar.pushMessage("Custom message", level=MessageLevel.WARNING)
```

## Static Helper Methods

Child widgets can push messages without holding a direct reference to the message bar:

```python
from pgserviceparser.gui import MessageBar

class MyWidget(QWidget):
    def save_data(self):
        try:
            write_to_disk()
            MessageBar.pushSuccessToBar(self, "Data saved successfully")
        except Exception as e:
            MessageBar.pushErrorToBar(self, "Could not save data", e)
```

The static helper methods automatically walk up the widget tree to find the nearest `MessageBar`.

## API Reference

::: pgserviceparser.gui.MessageBar
    options:
      show_source: false
      members:
        - pushMessage
        - pushSuccess
        - pushWarning
        - pushError
        - clearAll
        - findMessageBar
        - pushErrorToBar
        - pushWarningToBar
        - pushSuccessToBar

::: pgserviceparser.gui.MessageLevel
    options:
      show_source: false
