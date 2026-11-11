#!/usr/bin/env python3

from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse, parse_qs, quote
from email.parser import BytesParser
from email.policy import default
from io import BytesIO
import json
import mimetypes
import re
import zipfile
import html
import argparse
import ipaddress

DEFAULT_PORT = 8000
ROOT = Path(__file__).resolve().parent / "shared"
ROOT.mkdir(parents=True, exist_ok=True)


def safe_path(relative):
    relative = relative.replace("\\", "/")
    parts = PurePosixPath(relative).parts

    if not parts or any(p in ("..", "/", "\\") for p in parts):
        raise ValueError("Invalid path")

    if ":" in parts[0]:
        raise ValueError("Invalid path")

    target = (ROOT / Path(*parts)).resolve()
    target.relative_to(ROOT.resolve())
    return target


class Handler(BaseHTTPRequestHandler):

    def respond(self, status, data, content_type="text/plain"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def json_response(self, data, status=200):
        self.respond(
            status,
            json.dumps(data).encode(),
            "application/json"
        )

    def get_path(self):
        query = parse_qs(urlparse(self.path).query)
        return query.get("path", [""])[0]

    def do_GET(self):

        parsed = urlparse(self.path)

        if parsed.path == "/":
            self.respond(200, PAGE.encode(), "text/html; charset=utf-8")
            return

        if parsed.path == "/api/list":
            try:
                relative = self.get_path()
                folder = ROOT if not relative else safe_path(relative)

                if not folder.is_dir():
                    raise ValueError("Not a directory")

                entries = []

                for item in sorted(
                    folder.iterdir(),
                    key=lambda p: (not p.is_dir(), p.name.lower())
                ):
                    if item.is_symlink():
                        continue

                    entries.append({
                        "name": item.name,
                        "directory": item.is_dir(),
                        "size": item.stat().st_size if item.is_file() else 0
                    })

                self.json_response({
                    "path": relative,
                    "entries": entries
                })

            except Exception as e:
                self.json_response({"error": str(e)}, 400)

            return

        if parsed.path == "/api/download":
            try:
                target = safe_path(self.get_path())

                if not target.is_file() or target.is_symlink():
                    raise ValueError("File not found")

                filename = target.name
                mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"

                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header(
                    "Content-Disposition",
                    f"attachment; filename*=UTF-8''{quote(filename)}"
                )
                self.send_header("Content-Length", str(target.stat().st_size))
                self.end_headers()

                with target.open("rb") as f:
                    while True:
                        chunk = f.read(1024 * 1024)
                        if not chunk:
                            break
                        self.wfile.write(chunk)

            except Exception as e:
                self.respond(400, str(e).encode())

            return

        if parsed.path == "/api/zip":
            try:
                relative = self.get_path()
                folder = ROOT if not relative else safe_path(relative)

                if not folder.is_dir():
                    raise ValueError("Not a directory")

                buffer = BytesIO()

                with zipfile.ZipFile(
                    buffer, "w", zipfile.ZIP_DEFLATED
                ) as archive:

                    for item in folder.rglob("*"):
                        if item.is_symlink() or not item.is_file():
                            continue

                        archive.write(
                            item,
                            item.relative_to(folder.parent)
                        )

                data = buffer.getvalue()
                filename = (folder.name or "ubuntu-files") + ".zip"

                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header(
                    "Content-Disposition",
                    f"attachment; filename*=UTF-8''{quote(filename)}"
                )
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            except Exception as e:
                self.respond(400, str(e).encode())

            return

        self.respond(404, b"Not found")

    def do_POST(self):

        if urlparse(self.path).path != "/api/upload":
            self.respond(404, b"Not found")
            return

        try:
            length = int(self.headers.get("Content-Length", 0))

            if length <= 0:
                raise ValueError("Empty upload")

            body = self.rfile.read(length)

            message = BytesParser(policy=default).parsebytes(
                b"Content-Type: " +
                self.headers["Content-Type"].encode() +
                b"\r\nMIME-Version: 1.0\r\n\r\n" +
                body
            )

            uploaded = []

            for part in message.iter_parts():

                filename = part.get_filename()

                if not filename:
                    continue

                target = safe_path(filename)
                target.parent.mkdir(parents=True, exist_ok=True)

                content = part.get_payload(decode=True) or b""

                with target.open("wb") as f:
                    f.write(content)

                uploaded.append(filename)

            self.json_response({
                "success": True,
                "uploaded": uploaded
            })

            print("Received:", uploaded)

        except Exception as e:
            self.json_response({"error": str(e)}, 400)


PAGE = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ubuntu File Transfer</title>

<style>
body {
    font-family: Arial, sans-serif;
    max-width: 950px;
    margin: 35px auto;
    padding: 0 18px;
    background: #f4f5f7;
    color: #222;
}
h1 { margin-bottom: 5px; }
.subtitle { color: #666; margin-bottom: 25px; }

.panel {
    background: white;
    border: 1px solid #ddd;
    border-radius: 9px;
    padding: 20px;
    margin-bottom: 20px;
}

button, .button {
    background: #2563eb;
    color: white;
    border: 0;
    padding: 10px 16px;
    border-radius: 5px;
    cursor: pointer;
    display: inline-block;
    text-decoration: none;
    margin: 4px 3px 4px 0;
}
button:hover, .button:hover { background: #1d4ed8; }

input[type=file] { margin: 12px 0; }

#progress {
    width: 100%;
    margin-top: 12px;
}

#status {
    margin-top: 10px;
    white-space: pre-wrap;
    color: #2563eb;
}

#breadcrumb {
    margin: 15px 0;
    overflow-wrap: anywhere;
}

.entry {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    border-top: 1px solid #eee;
    padding: 12px 3px;
}

.entry-name { overflow-wrap: anywhere; }
.entry-actions { flex-shrink: 0; }

.small {
    font-size: 12px;
    color: #777;
}

@media(max-width: 550px) {
    .entry { align-items: flex-start; flex-direction: column; }
}
</style>
</head>

<body>

<h1>Ubuntu File Transfer</h1>
<div class="subtitle">Windows ↔ Ubuntu | Local Ethernet connection</div>

<div class="panel">
    <h2>Windows → Ubuntu</h2>
    <p>Select individual files or entire directories.</p>

    <label>
        <b>Select files</b><br>
        <input type="file" id="files" multiple>
    </label>

    <br>

    <label>
        <b>Select folders</b><br>
        <input type="file" id="folders" webkitdirectory multiple>
    </label>

    <br>
    <button id="upload">Upload to Ubuntu</button>

    <progress id="progress" value="0" max="100" style="display:none"></progress>
    <div id="status" aria-live="polite"></div>
</div>

<div class="panel">
    <h2>Ubuntu → Windows</h2>
    <p>Browse files stored in the Ubuntu shared directory.</p>

    <div id="breadcrumb"></div>
    <div id="listing">Loading...</div>
</div>

<script>
const filesInput = document.getElementById("files");
const foldersInput = document.getElementById("folders");
const progress = document.getElementById("progress");
const status = document.getElementById("status");

let currentPath = "";

function api(path, relative) {
    return path + "?path=" + encodeURIComponent(relative);
}

function download(path) {
    window.location.href = api("/api/download", path);
}

function downloadZip(path) {
    window.location.href = api("/api/zip", path);
}

async function browse(path = "") {
    currentPath = path;

    const listing = document.getElementById("listing");
    const breadcrumb = document.getElementById("breadcrumb");

    listing.textContent = "Loading...";
    breadcrumb.replaceChildren();

    const home = document.createElement("button");
    home.textContent = "🏠 Shared folder";
    home.onclick = () => browse("");
    breadcrumb.append(home);

    let accumulated = "";

    for (const part of path.split("/").filter(Boolean)) {
        accumulated += (accumulated ? "/" : "") + part;

        const button = document.createElement("button");
        button.textContent = " / " + part;

        const target = accumulated;
        button.onclick = () => browse(target);

        breadcrumb.append(button);
    }

    try {
        const response = await fetch(api("/api/list", path));
        const data = await response.json();

        if (!response.ok) throw new Error(data.error);

        listing.replaceChildren();

        if (path) {
            const back = document.createElement("button");
            back.textContent = "⬅ Parent folder";
            back.onclick = () => browse(path.split("/").slice(0, -1).join("/"));
            listing.append(back);
        }

        if (!data.entries.length) {
            const empty = document.createElement("p");
            empty.textContent = "This folder is empty.";
            listing.append(empty);
        }

        for (const item of data.entries) {
            const row = document.createElement("div");
            row.className = "entry";

            const name = document.createElement("span");
            name.className = "entry-name";
            name.textContent = (item.directory ? "📁 " : "📄 ") + item.name;

            const actions = document.createElement("span");
            actions.className = "entry-actions";

            const fullPath = path ? path + "/" + item.name : item.name;

            if (item.directory) {
                const open = document.createElement("button");
                open.textContent = "Open";
                open.onclick = () => browse(fullPath);
                actions.append(open);

                const zip = document.createElement("button");
                zip.textContent = "Download ZIP";
                zip.onclick = () => downloadZip(fullPath);
                actions.append(zip);

            } else {
                const get = document.createElement("button");
                get.textContent = "Download";
                get.onclick = () => download(fullPath);
                actions.append(get);

                const size = document.createElement("span");
                size.className = "small";
                size.textContent = " " + formatSize(item.size);
                actions.append(size);
            }

            row.append(name, actions);
            listing.append(row);
        }

        const zipAll = document.createElement("button");
        zipAll.textContent = "Download current folder as ZIP";
        zipAll.onclick = () => downloadZip(path);
        listing.append(zipAll);

    } catch (error) {
        listing.textContent = "Error: " + error.message;
    }
}

function formatSize(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
    if (bytes < 1073741824) return (bytes / 1048576).toFixed(1) + " MB";
    return (bytes / 1073741824).toFixed(2) + " GB";
}

document.getElementById("upload").onclick = () => {

    const selected = [
        ...Array.from(filesInput.files).map(f => ({
            file: f,
            path: f.name
        })),

        ...Array.from(foldersInput.files).map(f => ({
            file: f,
            path: f.webkitRelativePath || f.name
        }))
    ];

    if (!selected.length) {
        status.textContent = "Please select files or folders first.";
        return;
    }

    if (!confirm(
        "Upload " + selected.length +
        " file(s) to Ubuntu? Existing files with the same paths will be overwritten."
    )) return;

    const form = new FormData();

    for (const item of selected) {
        form.append("files", item.file, item.path);
    }

    const xhr = new XMLHttpRequest();

    progress.style.display = "block";
    progress.value = 0;
    status.textContent = "Uploading...";

    xhr.open("POST", "/api/upload");

    xhr.upload.onprogress = event => {
        if (event.lengthComputable) {
            progress.value = event.loaded / event.total * 100;
            status.textContent =
                "Uploading: " + progress.value.toFixed(1) + "%";
        }
    };

    xhr.onload = () => {
        try {
            const result = JSON.parse(xhr.responseText);

            if (xhr.status >= 200 && xhr.status < 300) {
                status.textContent =
                    "Upload complete!\n" +
                    result.uploaded.join("\n");
                filesInput.value = "";
                foldersInput.value = "";
                browse(currentPath);
            } else {
                status.textContent = "Upload failed: " + result.error;
            }
        } catch {
            status.textContent = "Upload failed: " + xhr.responseText;
        }
    };

    xhr.onerror = () => {
        status.textContent = "Network error during upload.";
    };

    xhr.send(form);
};

browse();
</script>

</body>
</html>
"""


class ThreadedServer(HTTPServer):
    allow_reuse_address = True


def main():

    parser = argparse.ArgumentParser(
        description="Ubuntu File Transfer Server"
    )

    parser.add_argument(
        "ip",
        help="IP address assigned to the Ubuntu network interface"
    )

    parser.add_argument(
        "port",
        nargs="?",
        type=int,
        default=DEFAULT_PORT,
        help=f"Server port (default: {DEFAULT_PORT})"
    )

    args = parser.parse_args()

    try:
        ipaddress.ip_address(args.ip)
    except ValueError:
        parser.error("Invalid IP address")

    if not 1 <= args.port <= 65535:
        parser.error("Port must be between 1 and 65535")

    print("=" * 55)
    print("Ubuntu File Transfer Server")
    print("=" * 55)
    print(f"Address: http://{args.ip}:{args.port}")
    print(f"Shared directory: {ROOT}")
    print("Press Ctrl+C to stop.")
    print("=" * 55)

    try:
        server = ThreadedServer((args.ip, args.port), Handler)
        server.serve_forever()

    except OSError as e:
        print(f"Unable to start server: {e}")

    except KeyboardInterrupt:
        print("\nServer stopped.")

    finally:
        if 'server' in locals():
            server.server_close()


if __name__ == "__main__":
    main()
