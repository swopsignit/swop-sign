<?php
/**
 * Tekent één release met Ed25519 (sodium). Draait alleen in de job "tekenen", na akkoord van de reviewer.
 *
 * Gebruik: php teken.php <kind> <slug> <versie> <sha256> <commit>
 * De geheime sleutel komt uit de omgevingsvariabele SWOP_SIGN_KEY (base64, 64 bytes) en wordt nooit getoond.
 * Uitvoer (stdout): de handtekening als JSON, precies zoals de Bridge hem verwacht.
 * Bericht (gelijk aan Swop_Bridge_Sign::message in de Bridge):
 *   swop-sign/v1\nkind:..\nslug:..\nversion:..\nsha256:..\ncommit:..\nsigned_at:..
 */

if ( $argc < 6 ) {
	fwrite( STDERR, "Te weinig argumenten.\n" );
	exit( 1 );
}
list( , $kind, $slug, $version, $sha, $commit ) = $argv;
$sha    = strtolower( $sha );
$commit = strtolower( $commit );
if ( ! in_array( $kind, array( 'plugin', 'theme', 'bridge' ), true )
	|| ! preg_match( '/^[a-z0-9]+(-[a-z0-9]+)*$/', $slug )
	|| ! preg_match( '/^\d+\.\d+\.\d+$/', $version )
	|| ! preg_match( '/^[0-9a-f]{64}$/', $sha )
	|| ! preg_match( '/^[0-9a-f]{40}$/', $commit ) ) {
	fwrite( STDERR, "Ongeldige invoer.\n" );
	exit( 1 );
}
$secret = base64_decode( (string) getenv( 'SWOP_SIGN_KEY' ), true );
if ( false === $secret || SODIUM_CRYPTO_SIGN_SECRETKEYBYTES !== strlen( $secret ) ) {
	fwrite( STDERR, "SWOP_SIGN_KEY ontbreekt of is ongeldig.\n" );
	exit( 1 );
}
$public    = sodium_crypto_sign_publickey_from_secretkey( $secret );
$signed_at = time();
$message   = implode( "\n", array( 'swop-sign/v1', 'kind:' . $kind, 'slug:' . $slug, 'version:' . $version, 'sha256:' . $sha, 'commit:' . $commit, 'signed_at:' . $signed_at ) );
$sig       = sodium_crypto_sign_detached( $message, $secret );
sodium_memzero( $secret );
if ( ! sodium_crypto_sign_verify_detached( $sig, $message, $public ) ) {
	fwrite( STDERR, "Zelfcontrole van de handtekening mislukt.\n" );
	exit( 1 );
}
echo json_encode(
	array(
		'v'         => 1,
		'key'       => substr( hash( 'sha256', $public ), 0, 16 ),
		'sig'       => base64_encode( $sig ),
		'kind'      => $kind,
		'slug'      => $slug,
		'version'   => $version,
		'sha256'    => $sha,
		'commit'    => $commit,
		'signed_at' => $signed_at,
	),
	JSON_UNESCAPED_SLASHES
);
