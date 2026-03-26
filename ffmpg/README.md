# ffmpg

Because lambda layers aren't available (thanks rosetta hub) I packaged my own ffmpeg using docker and this command:

```sh
sudo docker run --rm -v $PWD:/host amazonlinux:2 bash -c "
  yum install -y tar xz wget zip binutils && \
  mkdir -p /tmp/layer/bin && \
  cd /tmp && \
  wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz && \
  tar -xvf ffmpeg-release-amd64-static.tar.xz && \
  cp ffmpeg-7.0.2-amd64-static/ffmpeg /tmp/layer/bin/ && \
  cp ffmpeg-7.0.2-amd64-static/ffprobe /tmp/layer/bin/ && \
  strip --strip-all /tmp/layer/bin/ffmpeg /tmp/layer/bin/ffprobe && \
  cd /tmp/layer && \
  zip -9 -r /host/ffmpeg-layer.zip bin"
```

Except it doesn't work because it's 56mb and AWS requires 50mb.

```sh
sudo docker run --rm -v $PWD:/host amazonlinux:2 bash -c "
  yum groupinstall -y 'Development Tools' && \
  yum install -y autoconf automake libtool pkgconfig git wget xz tar make nasm yasm zlib-devel && \
  mkdir -p /tmp/layer/bin /tmp/ffmpeg && cd /tmp/ffmpeg && \
  git clone https://git.ffmpeg.org/ffmpeg.git ffmpeg && cd ffmpeg && \
  ./configure \
    --prefix=/tmp/layer \
    --disable-debug \
    --disable-doc \
    --disable-ffplay \
    --disable-network \
    --disable-avfilter \
    --disable-swresample \
    --disable-swscale \
    --enable-small \
    --enable-static \
    --disable-shared \
    --enable-ffmpeg \
    --enable-ffprobe && \
  make -j\$(nproc) && make install && \
  [ -f /tmp/layer/bin/ffmpeg ] && strip --strip-all /tmp/layer/bin/ffmpeg /tmp/layer/bin/ffprobe || true && \
  cd /tmp/layer && zip -9 -r /host/ffmpeg-layer.zip bin
"
```

Luckily, building ffmpeg from scratch DOES work and produces a zip of ~36MB.


