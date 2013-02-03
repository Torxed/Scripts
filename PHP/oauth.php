<?php
class oauth_client {
    function set_customer_key($key) {
        $this->key = $key;
    }
    function set_customer_secret($key) {
        $this->secret = $key;
    }
    function set_token_secret($key) {
        $this->token_secret = $key;
    }
    function set_token($key) {
        $this->token = $key;
    }
    function request_token($callback_url) {


        $query = array(
            'oauth_consumer_key'=>$this->key,
            'oauth_signature_method'=>'HMAC-SHA1',
            'oauth_timestamp'=>time(),
            'oauth_nonce'=>123,
            'oauth_callback' => $callback_url
        );

        $parameters = array();
        ksort($query);
        foreach($query as $key => $line) {
            $parameters[urlencode($key)] = urlencode($line);
        }

        $base_string = 'GET&'.urlencode('http://api.crew.dreamhack.se/oauth/request_token').'&'.urlencode(http_build_query($query));

        $query['oauth_signature'] = $this->sign($base_string, $this->secret,'');
        
        $resp = file_get_contents("http://api.crew.dreamhack.se/oauth/request_token?".http_build_query($query));
        $resp = json_decode($resp,true);

        return $resp;
    }

    function access_token($token,$verifier) {

        $query = array(
            'oauth_consumer_key'=>$this->key,
            'oauth_signature_method'=>'HMAC-SHA1',
            'oauth_timestamp'=>time(),
            'oauth_nonce'=>123,
            'oauth_token'=>$token
        );

        $parameters = array();
        foreach($query as $key => $line) {
            $parameters[urlencode($key)] = urlencode($line);
        }
        $parameters['oauth_verifier'] = urlencode($verifier);
        ksort($parameters);

        $base_string = 'POST&'.urlencode('http://api.crew.dreamhack.se/oauth/access_token').'&'.urlencode(http_build_query($parameters));
        $query['oauth_signature'] = $this->sign($base_string, $this->secret,$this->token_secret);
        
        $resp = $this->do_post_request("http://api.crew.dreamhack.se/oauth/access_token?".http_build_query($query),'oauth_verifier='.$verifier);
        $resp = json_decode($resp,true);

        return $resp;
    }

    function sign ( $base_string, $consumer_secret, $token_secret )/*{{{*/
    {
        $key = urlencode($consumer_secret).'&'.urlencode($token_secret);

        if (function_exists('hash_hmac')) {
            $signature = base64_encode(hash_hmac("sha1", $base_string, $key, true));
        } else {
            $blocksize  = 64;
            $hashfunc   = 'sha1';
            if (strlen($key) > $blocksize) {;
                $key = pack('H*', $hashfunc($key));
            }
            $key     = str_pad($key,$blocksize,chr(0x00));
            $ipad    = str_repeat(chr(0x36),$blocksize);
            $opad    = str_repeat(chr(0x5c),$blocksize);
            $hmac     = pack(
                        'H*',$hashfunc(
                            ($key^$opad).pack(
                                'H*',$hashfunc(
                                    ($key^$ipad).$base_string
                                )
                            )
                        )
                    );
            $signature = base64_encode($hmac);
        }
        return urlencode($signature);
    }/*}}}*/

    function do_post_request($url, $data, $optional_headers = null)
    {
        $params = array(
            'http' => array(
                  'method' => 'POST',
                  'content' => $data
            )
        );

        if ($optional_headers !== null) {
            $params['http']['header'] = $optional_headers;
        }

        $ctx = stream_context_create($params);
        $fp = @fopen($url, 'rb', false, $ctx);
        if (!$fp) {
            throw new Exception("Problem with $url, $php_errormsg");
        }
        $response = @stream_get_contents($fp);
        if ($response === false) {
            throw new Exception("Problem reading data from $url, $php_errormsg");
        }
        return $response;
    }

    function get($url) {
        $params = array(
            'http' => array(
                  'method' => 'GET',
            )
        );

        $query = array(
            'oauth_consumer_key'=>$this->key,
            'oauth_signature_method'=>'HMAC-SHA1',
            'oauth_timestamp'=>time(),
            'oauth_nonce'=>123,
            'oauth_token'=>$this->token
        );

        $parameters = array();
        ksort($query);
        foreach($query as $key => $line) {
            $parameters[urlencode($key)] = urlencode($line);
        }

        $base_string = 'GET&'.urlencode($url).'&'.urlencode(http_build_query($parameters));
        $query['oauth_signature'] = $this->sign($base_string, $this->secret,$this->token_secret);

        $params['http']['header'] = array(
            'Authorization: OAuth '.http_build_query($query)."\r\n",
        );

        print_r($params);

        $ctx = stream_context_create($params);
        $fp = fopen($url, 'rb', false, $ctx);
        if (!$fp) {
            throw new Exception("Problem with $url, $php_errormsg");
        }
        $response = @stream_get_contents($fp);
        if ($response === false) {
            throw new Exception("Problem reading data from $url, $php_errormsg");
        }
        return $response;
    }
}

$oauth = new oauth_client();

$oauth->{'set_customer_key'}("_________");
$oauth->{'set_customer_secret'}("_________");
$tokens = $oauth->{'request_token'}("http://127.0.0.1");

$oauth->{'set_token_secret'}($tokens['oauth_token_secret']);
$oauth->{'set_token'}($tokens['oauth_token']);

print $oauth->{'get'}('http://api.crew.dreamhack.se/1/user/get/635');

?>
