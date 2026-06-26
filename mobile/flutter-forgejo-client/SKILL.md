---
name: flutter-forgejo-client
description: Build Flutter apps that connect to a self-hosted Forgejo instance. Covers Flutter setup, thin API client pattern, Material 3 UI, and repo push.
triggers:
  - Building a Flutter app for Forgejo or Gitea
  - Creating a mobile client for a self-hosted Git forge
  - Writing Dart code that calls the Forgejo REST API
---

# Flutter Forgejo Client

Build Flutter apps that talk to a self-hosted Forgejo instance.

## Flutter Setup (Linux, no sudo)

Flutter SDK is installed at `~/.local/flutter/`. Prepend to PATH before any flutter/dart command:

```bash
export PATH="$HOME/.local/flutter/bin:$PATH"
```

Installed via tarball (not snap — snap requires sudo auth):

```bash
mkdir -p ~/.local/flutter
curl -sL "https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_<version>-stable.tar.xz" -o /tmp/flutter.tar.xz
tar -xf /tmp/flutter.tar.xz -C ~/.local/
```

**Note:** `flutter doctor` will likely report missing Android SDK on this headless machine. The project can still be created, analyzed (`flutter analyze`), and pushed — just not run locally. The user builds/runs on their own device.

## Project Scaffold

```bash
cd /home/ruben
export PATH="$HOME/.local/flutter/bin:$PATH"
flutter create --org dev.oathless --project-name <name> --platforms android <name>
cd <name>
flutter pub add http shared_preferences flutter_markdown
```

Dependencies (ponytail minimum):
- `http` — REST calls to Forgejo API (no generated client needed)
- `shared_preferences` — persist instance URL + token
- `flutter_markdown` — render READMEs and issue bodies (discontinued but functional; replace with `flutter_markdown_plus` if it breaks)

## Forgejo API Client Pattern

Don't reach for a generated OpenAPI package — none exist on pub.dev for Forgejo/Gitea that are maintained. A thin HTTP wrapper (~50 lines) covers all read operations.

Template: `references/client.dart`

Key points:
- Auth: `Authorization: token <token>` header
- Base URL pattern: `$baseUrl/api/v1<endpoint>`
- All list endpoints return JSON arrays, single objects return JSON maps
- Token scopes needed: `read:repository`, `read:issue`, `read:notification`, `read:user`

Endpoints used:
| Endpoint | Returns |
|----------|---------|
| `GET /user/repos` | List of repos |
| `GET /repos/{owner}/{repo}` | Repo detail |
| `GET /repos/{owner}/{repo}/contents/{path}` | File/dir listing (array for dirs, object for files) |
| `GET /repos/{owner}/{repo}/issues?state=open\|closed` | Issues list |
| `GET /repos/{owner}/{repo}/issues/{number}` | Single issue |
| `GET /repos/{owner}/{repo}/issues/{number}/comments` | Issue comments |
| `GET /notifications` | Notification list |

File content is base64-encoded. Decode with:
```dart
String.fromCharCodes(base64Decode(content.replaceAll('\n', '')))
```

## App Structure (ponytail)

Fewest files that work:
- `lib/client.dart` — API client
- `lib/main.dart` — app shell, routing, all screens

No state management library — `setState` is sufficient for this scope. No routing framework — `MaterialPageRoute` + `Navigator.push` covers it.

## Pitfalls

- **Import placement:** `import 'dart:convert'` must appear before any package imports, not at the bottom of the file.
- **String interpolation:** `'$_path/${f['name']}'` — simple variables don't need braces inside strings. `'${_path}/${f['name']}'` triggers a lint warning.
- **flutter_markdown discontinued:** Package is marked discontinued (replaced by `flutter_markdown_plus`). It still works. Swap if it breaks on a future Flutter version.
- **No Android SDK on this machine:** `flutter run` won't work here. The user runs it on their own device. Verify with `flutter analyze` only.

## Push to Forgejo

Same repo-creation pattern as other projects. See `go-vue-fullstack` skill, reference `forgejo-repo-create.md`. Token scopes are read-only for this app — no write API calls implemented.

```bash
cd /home/ruben/<project>
git init && git add -A && git commit -m "Initial commit"
# Create repo via API (see forgejo-repo-create.md), verify private, then:
git remote add origin https://git.oathless.dev/oathless/<project>.git
git push -u origin master
```
