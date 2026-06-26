import 'dart:convert';
import 'package:http/http.dart' as http;

/// Thin wrapper around the Forgejo/Gitea REST API.
/// Covers read-only operations: repos, files, issues, notifications.
class ForgejoClient {
  final String baseUrl;
  final String token;
  final http.Client _http;

  ForgejoClient({required this.baseUrl, required this.token})
      : _http = http.Client();

  Map<String, String> get _headers => {
        'Authorization': 'token $token',
        'Content-Type': 'application/json',
      };

  String _url(String path) => '$baseUrl/api/v1$path';

  Future<dynamic> _get(String path) async {
    final response = await _http.get(Uri.parse(_url(path)), headers: _headers);
    if (response.statusCode == 200) return jsonDecode(response.body);
    throw Exception('${response.statusCode}: ${response.body}');
  }

  Future<List<dynamic>> listRepos() async =>
      List<dynamic>.from(await _get('/user/repos'));

  Future<Map<String, dynamic>> getRepo(String owner, String repo) async =>
      Map<String, dynamic>.from(await _get('/repos/$owner/$repo'));

  Future<dynamic> getContents(String owner, String repo, String path) async =>
      await _get('/repos/$owner/$repo/contents/$path');

  Future<List<dynamic>> listIssues(String owner, String repo,
          {String state = 'open'}) async =>
      List<dynamic>.from(
          await _get('/repos/$owner/$repo/issues?state=$state'));

  Future<Map<String, dynamic>> getIssue(
          String owner, String repo, int number) async =>
      Map<String, dynamic>.from(
          await _get('/repos/$owner/$repo/issues/$number'));

  Future<List<dynamic>> getComments(
          String owner, String repo, int issueNumber) async =>
      List<dynamic>.from(
          await _get('/repos/$owner/$repo/issues/$issueNumber/comments'));

  Future<List<dynamic>> listNotifications() async =>
      List<dynamic>.from(await _get('/notifications'));

  void dispose() => _http.close();
}
