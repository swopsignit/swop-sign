<?php
/**
 * Maakt een nieuw Ed25519-sleutelpaar. Alleen voor de workflow "Sleutel maken".
 *
 * Schrijft de geheime sleutel (base64) naar het bestand in argument 1 (rechten 600) en de publieke gegevens als JSON
 * naar stdout. De geheime sleutel komt nooit op het scherm of in het logboek.
 */

if ( $argc < 2 ) {
	fwrite( STDERR, "Geef het pad voor de geheime sleutel.\n" );
	exit( 1 );
}
$pair   = sodium_crypto_sign_keypair();
$secret = sodium_crypto_sign_secretkey( $pair );
$public = sodium_crypto_sign_publickey( $pair );
umask( 077 );
if ( false === file_put_contents( $argv[1], base64_encode( $secret ) ) ) {
	fwrite( STDERR, "Kon de geheime sleutel niet wegschrijven.\n" );
	exit( 1 );
}
sodium_memzero( $secret );
sodium_memzero( $pair );
echo json_encode(
	array(
		'key_id'     => substr( hash( 'sha256', $public ), 0, 16 ),
		'public_key' => base64_encode( $public ),
	)
);
