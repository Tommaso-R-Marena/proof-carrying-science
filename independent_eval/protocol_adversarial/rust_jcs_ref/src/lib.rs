//! Independent JCS (RFC 8785) canonicalization and SHA-256 helpers.
//!
//! This crate intentionally does **not** import or call PCS Python code.
//! Differential tests compare its outputs against PCS for disagreement logging.

use serde_json::Value;
use sha2::{Digest, Sha256};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum JcsError {
    #[error("JSON parse error: {0}")]
    Parse(String),
    #[error("duplicate object key: {0}")]
    DuplicateKey(String),
    #[error("non-finite number")]
    NonFinite,
    #[error("unsupported value")]
    Unsupported,
    #[error("lone Unicode surrogate / noncharacter rejected")]
    BadUnicode,
}

/// UTF-16 code unit sort key for object member names (RFC 8785).
fn utf16_key(s: &str) -> Vec<u16> {
    s.encode_utf16().collect()
}

fn validate_string(s: &str) -> Result<(), JcsError> {
    for ch in s.chars() {
        let cp = ch as u32;
        if (0xD800..=0xDFFF).contains(&cp) {
            return Err(JcsError::BadUnicode);
        }
        if (0xFDD0..=0xFDEF).contains(&cp) || (cp & 0xFFFF) == 0xFFFE || (cp & 0xFFFF) == 0xFFFF {
            return Err(JcsError::BadUnicode);
        }
    }
    Ok(())
}

/// Serialize a finite f64 with ECMAScript / JCS spelling (approximate; matches PCS on common cases).
fn serialize_number(n: f64) -> Result<String, JcsError> {
    if !n.is_finite() {
        return Err(JcsError::NonFinite);
    }
    if n == 0.0 {
        return Ok("0".to_string());
    }
    // Prefer Rust Display spelling; differential tests record remaining PCS mismatches.
    let shortest = n.to_string().to_lowercase();
    if shortest == "-0" {
        return Ok("0".to_string());
    }
    Ok(shortest)
}

pub fn canonicalize(value: &Value) -> Result<String, JcsError> {
    match value {
        Value::Null => Ok("null".into()),
        Value::Bool(true) => Ok("true".into()),
        Value::Bool(false) => Ok("false".into()),
        Value::Number(num) => {
            let f = num.as_f64().ok_or(JcsError::NonFinite)?;
            serialize_number(f)
        }
        Value::String(s) => {
            validate_string(s)?;
            Ok(serde_json::to_string(s).map_err(|e| JcsError::Parse(e.to_string()))?)
        }
        Value::Array(items) => {
            let mut out = String::from("[");
            for (i, item) in items.iter().enumerate() {
                if i > 0 {
                    out.push(',');
                }
                out.push_str(&canonicalize(item)?);
            }
            out.push(']');
            Ok(out)
        }
        Value::Object(map) => {
            let mut keys: Vec<&String> = map.keys().collect();
            keys.sort_by(|a, b| utf16_key(a).cmp(&utf16_key(b)));
            let mut out = String::from("{");
            for (i, key) in keys.iter().enumerate() {
                if i > 0 {
                    out.push(',');
                }
                validate_string(key)?;
                out.push_str(&serde_json::to_string(key).map_err(|e| JcsError::Parse(e.to_string()))?);
                out.push(':');
                out.push_str(&canonicalize(&map[*key])?);
            }
            out.push('}');
            Ok(out)
        }
    }
}

pub fn parse_rejecting_duplicates(raw: &str) -> Result<Value, JcsError> {
    // serde_json collapses duplicates by default; use a scanner for duplicate keys.
    detect_duplicate_keys(raw)?;
    serde_json::from_str(raw).map_err(|e| JcsError::Parse(e.to_string()))
}

fn detect_duplicate_keys(raw: &str) -> Result<(), JcsError> {
    // Lightweight brace/object walk using serde_json::Deserializer is complex;
    // for vectors we use a recursive Value check after parse is insufficient.
    // Scan object scopes with a simple recursive parser for keys.
    scan_keys(raw.as_bytes(), 0).map(|_| ())
}

fn skip_ws(bytes: &[u8], mut i: usize) -> usize {
    while i < bytes.len() && matches!(bytes[i], b' ' | b'\t' | b'\n' | b'\r') {
        i += 1;
    }
    i
}

fn scan_keys(bytes: &[u8], mut i: usize) -> Result<usize, JcsError> {
    i = skip_ws(bytes, i);
    if i >= bytes.len() {
        return Ok(i);
    }
    match bytes[i] {
        b'{' => {
            i += 1;
            let mut seen = std::collections::HashSet::new();
            i = skip_ws(bytes, i);
            if i < bytes.len() && bytes[i] == b'}' {
                return Ok(i + 1);
            }
            loop {
                i = skip_ws(bytes, i);
                if i >= bytes.len() || bytes[i] != b'"' {
                    return Err(JcsError::Parse("expected object key".into()));
                }
                let (key, next) = parse_string(bytes, i)?;
                if !seen.insert(key.clone()) {
                    return Err(JcsError::DuplicateKey(key));
                }
                i = skip_ws(bytes, next);
                if i >= bytes.len() || bytes[i] != b':' {
                    return Err(JcsError::Parse("expected colon".into()));
                }
                i = scan_keys(bytes, i + 1)?;
                i = skip_ws(bytes, i);
                if i < bytes.len() && bytes[i] == b',' {
                    i += 1;
                    continue;
                }
                if i < bytes.len() && bytes[i] == b'}' {
                    return Ok(i + 1);
                }
                return Err(JcsError::Parse("expected comma or end of object".into()));
            }
        }
        b'[' => {
            i += 1;
            i = skip_ws(bytes, i);
            if i < bytes.len() && bytes[i] == b']' {
                return Ok(i + 1);
            }
            loop {
                i = scan_keys(bytes, i)?;
                i = skip_ws(bytes, i);
                if i < bytes.len() && bytes[i] == b',' {
                    i += 1;
                    continue;
                }
                if i < bytes.len() && bytes[i] == b']' {
                    return Ok(i + 1);
                }
                return Err(JcsError::Parse("expected comma or end of array".into()));
            }
        }
        b'"' => {
            let (_s, next) = parse_string(bytes, i)?;
            Ok(next)
        }
        b't' | b'f' | b'n' => {
            // true/false/null
            while i < bytes.len() && bytes[i].is_ascii_alphabetic() {
                i += 1;
            }
            Ok(i)
        }
        b'-' | b'0'..=b'9' => {
            while i < bytes.len()
                && (bytes[i].is_ascii_digit()
                    || matches!(bytes[i], b'-' | b'+' | b'.' | b'e' | b'E'))
            {
                i += 1;
            }
            Ok(i)
        }
        _ => Err(JcsError::Parse(format!("unexpected byte at {i}"))),
    }
}

fn parse_string(bytes: &[u8], mut i: usize) -> Result<(String, usize), JcsError> {
    if bytes.get(i) != Some(&b'"') {
        return Err(JcsError::Parse("expected string".into()));
    }
    i += 1;
    let mut out = String::new();
    while i < bytes.len() {
        match bytes[i] {
            b'"' => return Ok((out, i + 1)),
            b'\\' => {
                i += 1;
                if i >= bytes.len() {
                    return Err(JcsError::Parse("truncated escape".into()));
                }
                match bytes[i] {
                    b'"' | b'\\' | b'/' => {
                        out.push(bytes[i] as char);
                        i += 1;
                    }
                    b'b' => {
                        out.push('\u{0008}');
                        i += 1;
                    }
                    b'f' => {
                        out.push('\u{000c}');
                        i += 1;
                    }
                    b'n' => {
                        out.push('\n');
                        i += 1;
                    }
                    b'r' => {
                        out.push('\r');
                        i += 1;
                    }
                    b't' => {
                        out.push('\t');
                        i += 1;
                    }
                    b'u' => {
                        if i + 4 >= bytes.len() {
                            return Err(JcsError::Parse("truncated unicode escape".into()));
                        }
                        let hex = std::str::from_utf8(&bytes[i + 1..i + 5])
                            .map_err(|e| JcsError::Parse(e.to_string()))?;
                        let cp = u32::from_str_radix(hex, 16)
                            .map_err(|e| JcsError::Parse(e.to_string()))?;
                        out.push(char::from_u32(cp).ok_or(JcsError::BadUnicode)?);
                        i += 5;
                    }
                    _ => return Err(JcsError::Parse("bad escape".into())),
                }
            }
            c => {
                out.push(c as char);
                i += 1;
            }
        }
    }
    Err(JcsError::Parse("unterminated string".into()))
}

pub fn jcs_sha256_hex(value: &Value) -> Result<String, JcsError> {
    let text = canonicalize(value)?;
    let digest = Sha256::digest(text.as_bytes());
    Ok(hex::encode(digest))
}

pub fn sha256_bytes_hex(raw: &[u8]) -> String {
    hex::encode(Sha256::digest(raw))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn sorts_object_keys() {
        let v = json!({"b": 1, "a": 2});
        assert_eq!(canonicalize(&v).unwrap(), r#"{"a":2,"b":1}"#);
    }

    #[test]
    fn rejects_duplicate_keys() {
        let err = parse_rejecting_duplicates(r#"{"a":1,"a":2}"#).unwrap_err();
        assert!(matches!(err, JcsError::DuplicateKey(_)));
    }

    #[test]
    fn hash_stable() {
        let v = json!({"z": [1, 2], "a": null});
        let h1 = jcs_sha256_hex(&v).unwrap();
        let h2 = jcs_sha256_hex(&v).unwrap();
        assert_eq!(h1, h2);
        assert_eq!(h1.len(), 64);
    }
}
