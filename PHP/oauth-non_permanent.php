<?php
class oauth_client {
    function set_customer_key($key) {/*{{{*/
        $this->key = $key;
    }/*}}}*/
    function set_customer_secret($key) {/*{{{*/
        $this->secret = $key;
    }/*}}}*/
    function set_token_secret($key) {/*{{{*/
        $this->token_secret = $key;
    }/*}}}*/
    function set_token($key) {/*{{{*/
        $this->token = $key;
    }/*}}}*/

    function request_token($callback_url) {/*{{{*/
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

        $base_string = 'GET&'.urlencode('https://api.crew.dreamhack.se/oauth/request_token').'&'.urlencode(http_build_query($query));

        $query['oauth_signature'] = $this->sign($base_string, $this->secret,'');
        
        $resp = file_get_contents("https://api.crew.dreamhack.se/oauth/request_token?".http_build_query($query));
        $resp = json_decode($resp,true);

        return $resp;
    }/*}}}*/

    function access_token($token,$verifier) {/*{{{*/

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

        $base_string = 'POST&'.urlencode('https://api.crew.dreamhack.se/oauth/access_token').'&'.urlencode(http_build_query($parameters));
        $query['oauth_signature'] = $this->sign($base_string, $this->secret,$this->token_secret);
        
        $resp = $this->do_post_request("https://api.crew.dreamhack.se/oauth/access_token?".http_build_query($query),'oauth_verifier='.$verifier);
        $resp = json_decode($resp,true);

        return $resp;
    }/*}}}*/

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

    function do_post_request($url, $data, $optional_headers = null)/*{{{*/
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
    }/*}}}*/

    function get($url) {/*{{{*/
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

        $query_string = array();
        foreach($query as $key => $line)
            $query_string[] = "$key=\"$line\"";

        $params['http']['header'] = 'Authorization: OAuth '.implode(',',$query_string)."\r\n";

        $ctx = stream_context_create($params);
        $fp = fopen($url, 'rb', false, $ctx);
        if (!$fp) {
            throw new Exception("Problem with $url, $php_errormsg");
        }
        $response = @stream_get_contents($fp);
        if ($response === false) {
            throw new Exception("Problem reading data from $url, $php_errormsg");
        }
        return json_decode($response,true);
    }/*}}}*/
}

// This is a example how to use temporarily tokens for communication. The have a expire time on 1 hour after last access.

// Documentation is found here: https://api.crew.dreamhack.se/oauth/Introduction%20to%20OAuth.md

$oauth = new oauth_client();

// Set developer keys, used to identify the developer and application
    $oauth->{'set_customer_key'}("-------");
    $oauth->{'set_customer_secret'}("------");

// STEP 2 - Catch the returning user form the login page and save the new keys
    if ( isset($_GET['oauth_token']) && isset($_GET['oauth_verifier']) ) {
        // Save the token
        file_put_contents('temporarily_token',$_GET['oauth_token']);

        // Redirect the user to the normal page, not neccerary but looks nicer
        header('Location: https://'.$_SERVER['HTTP_HOST'].$_SERVER['SCRIPT_NAME'] ); 
        die();
    }

// Try to get a saved access_token, this is normaly done in the session
    $temp_token = file_get_contents('temporarily_token');

// STEP 1 - Get a request_token, this is used for enabling the login page
    if (!$temp_token) {
        $request_token = $oauth->request_token('https://'.$_SERVER['HTTP_HOST'].$_SERVER['SCRIPT_NAME']);

        // Save the secret (This should be done in the session or in the database!)
        file_put_contents('request_token_secret',$request_token['oauth_token_secret']);

        // Redirect the user to the login page
        header("Location: https://api.crew.dreamhack.se/oauth/authorize?oauth_token=".$request_token['oauth_token']);

        die();
    }

// STEP 3 - Use the temporarily_token to request data
    $oauth->set_token_secret(file_get_contents('request_token_secret'));
    $oauth->set_token($temp_token);

    // Get the desired data
    $result = $oauth->{'get'}('https://api.crew.dreamhack.se/1/user/get/635');

    // If there is a problem with the current session, delete keys
    if ( isset($result['oauth_problem']) ) {
        unlink('temporarily_token');
        unlink('request_token_secret');
    }

    print_r($result);

?>
