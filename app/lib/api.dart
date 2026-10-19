import 'dart:convert';
import 'dart:async';
import 'package:http/http.dart' as http;

class Api {
  static const base = String.fromEnvironment('API_URL', defaultValue: 'http://127.0.0.1:8000');
  String? token; // In memory only; never persisted into browser storage.
  Future<Map<String, dynamic>> call(String path, [Map<String, dynamic>? data]) async {
    final headers = <String, String>{'Content-Type': 'application/json', if (token != null) 'Authorization': 'Bearer $token'};
    final uri = Uri.parse('$base$path');
    late http.Response response;
    try {
      response = await (data == null ? http.get(uri, headers: headers) : http.post(uri, headers: headers, body: jsonEncode(data))).timeout(const Duration(seconds: 25));
    } on TimeoutException {
      throw Exception('The server took too long to respond. Refresh to check whether your change was saved before trying again.');
    } on http.ClientException {
      throw Exception('Cannot reach MachineCare. Check the backend connection, then retry.');
    }
    if (response.statusCode == 401) token = null;
    Map<String, dynamic> result;
    try { result = jsonDecode(response.body) as Map<String, dynamic>; }
    catch (_) { throw Exception('The server returned an unexpected response. Contact your administrator.'); }
    if (response.statusCode >= 400) throw Exception(result['error'] ?? 'Request failed.');
    return result;
  }
  Future<Map<String, dynamic>> login(String username, String password) async {
    final result = await call('/login', {'username': username, 'password': password});
    token = result['token'] as String;
    return result['user'] as Map<String, dynamic>;
  }
  Future<Map<String, dynamic>> action(String name, Map<String, dynamic> data) => call('/actions/$name', data);
}
