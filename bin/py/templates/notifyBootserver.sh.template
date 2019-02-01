#!/bin/bash

while true; do
  curl "http://@bootserver_ip@:@bootserver_listen_port@/installationCompleted?hostname=@target_hostname@"
  RC=$?
  if [ $RC -eq 0 ]; then
    break
  else
    sleep 10
  fi
done
