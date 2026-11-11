# NetDrop

A lightweight, browser-based, two-way file transfer server written entirely in Python's standard library.

Transfer files and directories between Windows and Ubuntu over a local network without installing additional software on the Windows machine.

No internet connection, third-party Python packages, or administrator privileges are required.

## Features

### Windows → Ubuntu
- Upload individual files.
- Upload multiple files simultaneously.
- Upload entire directories.
- Preserve nested directory structures.
- Upload progress indicator.
- Confirmation before uploading (existing files with identical paths are overwritten).

### Ubuntu → Windows
- Browse the shared directory through a web interface.
- Navigate nested directories.
- Download individual files.
- Download entire directories as ZIP archives.
- Download the contents of the current directory as a ZIP archive.

### General
- Two-way file transfer.
- Simple browser-based interface.
- Configurable IP address and port.
- Manually started and stopped.
- No background services.
- No external dependencies.

## Requirements

**Ubuntu**
- Python 3.9 or newer.
- A network interface with an assigned IP address.

**Windows**
- Microsoft Edge, Firefox, Chrome, or another modern browser.
- No additional software installation required.

## Installation

Clone the repository:

```bash
git clone <repository-url>
cd <repository-directory>
```

No Python packages need to be installed.

## Usage

Start the server by specifying the IP address assigned to the Ubuntu network interface:

```bash
python3 transfer_server.py 192.168.1.20
```

The default port is `8000`.

To use a different port:

```bash
python3 transfer_server.py 192.168.1.20 9000
```

Display available command-line options:

```bash
python3 transfer_server.py --help
```

### Finding your Ubuntu IP address

Use:

```bash
ip -br addr
```

Identify the IP address assigned to the network interface connected to your Windows machine.

The server must bind to an IP address actually assigned to Ubuntu.

### Accessing the server

Once started, the terminal displays the server address:

```text
=======================================================
Ubuntu File Transfer Server
=======================================================
Address: http://192.168.1.20:8000
Shared directory: /home/<username>/windows-transfer/shared
Press Ctrl+C to stop.
=======================================================
```

Open the displayed address in a browser on your Windows machine.

## Shared Directory

The server exposes the following directory:

```text
~/netdrop/shared/
```

Only files and directories inside this location are accessible through the web interface.

Place files in this directory to make them available for downloading from Windows.

Uploaded files and directories are also stored here.

The shared directory is intentionally excluded from Git version control.

## Security Considerations

**This project is intended for trusted local networks.**

- The server does not implement authentication or password protection.
- Anyone able to access the server can browse, download, and upload files.
- Existing files with matching paths are overwritten during uploads.
- The server binds to the explicitly supplied IP address rather than `0.0.0.0`.
- Symbolic links are excluded from directory listings and ZIP downloads.
- Path traversal attempts are rejected.

Only start the server on a trusted network.

Stop the server using `Ctrl+C` when file transfers are complete.

Do not expose the server to the public internet or untrusted networks.

## Limitations

- Uploads and ZIP archives are buffered in memory.
- Very large transfers may consume considerable RAM.
- ZIP downloads require sufficient memory to construct the archive.
- Uploads are not resumable.
- The server is single-threaded.
- No authentication or encryption is provided.

For ordinary local file transfers, these limitations are generally acceptable.

## Stopping the Server

Press:

```text
Ctrl+C
```

The server shuts down immediately.

There is no background service or automatic startup mechanism.

