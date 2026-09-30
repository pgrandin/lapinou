# CAD viewer on the homelab: lab deploy . --name lapinou  ->  http://lapinou.lab.lan
# viewer/ symlinks into output/, so copy the real files. The full assembly.step is
# generated locally and uncommitted; the glob keeps the build working without it.
FROM nginx:alpine
WORKDIR /usr/share/nginx/html
COPY viewer/index.html viewer/puck.html output/assembl[y].step ./
COPY viewer/vendor vendor/
COPY output/web/model.json ./
COPY output/web/assets assets/
COPY output/print print/
COPY output/led-puck led-puck/
EXPOSE 80
