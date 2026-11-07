%% Set-up
clear all; close all; 
clc

% page size
setLay.txt.width = 20.4; % breite max Bild (A4?)
setLay.txt.height = 29.1;

% font  
setLay.tit.size = 10;
setLay.tit.font = 'Times New Roman';
setLay.tit.weight = 'normal';

setLay.lab.size = 14;
setLay.lab.font = 'Helvetica';
setLay.lab.weight = 'bold';

setLay.ax.size = 10;
setLay.ax.font = 'Times New Roman';

%% Figure 2.2
%clc; close all; clearvars -except 'setLay'

% print
printBoolean = true;

% set figure properties
close all;
fig = figure(1);
f_width = 0.9*setLay.txt.width;
f_height = 0.5*setLay.txt.height;
set(fig,'Color',[1 1 1],...
        'Units','centimeters',...
        'Position', [0,0,f_width,f_height],...
        'PaperSize',[f_width f_height],...
        'PaperPosition', [0,0,f_width f_height],...
        'PaperSize', [f_width f_height])

% create axis
h = axes('Position',[0 0 1 1],'Visible','off');

ha(1) = axes('Position', [0.1, 0.1, 0.53, 0.8]);
ha(2) = axes('Position', [0.74, 0.54, 0.22, 0.36]);
%%

cur_dir = strrep(which('figureHopf'),'figureHopf.m','');
eval(['cd ' cur_dir]);

% load data
load('MS100_hopf.mat')
%%
Colvec = jet(10);
Colvec = max(Colvec-0.2,0);

%% Hopf limit set
theta = 0:0.1:4;
phi = linspace(0,2*pi,50);
x = sqrt(theta)'*cos(phi);
y = sqrt(theta)'*sin(phi);

%%
indStart = [2 5 6 12 29 39 45 46 47 55];

subplot(ha(1))
hold on
hl(2)=surf(x,y,repmat(theta',1,length(phi)));
shading interp
colormap gray(200)
alpha 0.5
hl(1)=plot3(zeros(2,1),zeros(2,1),[-4,0],'k','Linewidth',3);
for i=2:10
    plotInd = indStart(i);
    hl(i+1)=plot3(parameters_EM.MS.par_evol{plotInd}(:,2),parameters_EM.MS.par_evol{plotInd}(:,3),parameters_EM.MS.par_evol{plotInd}(:,1),'-','Color',Colvec(i,:));
    hold on;
    plot3(parameters_EM.MS.par(2,plotInd),parameters_EM.MS.par(3,plotInd),parameters_EM.MS.par(1,plotInd),'*','Color',Colvec(i,:))
    plot3(parameters_EM.MS.par0(2,plotInd),parameters_EM.MS.par0(3,plotInd),parameters_EM.MS.par0(1,plotInd),'o','Color',Colvec(i,:))
    zlabel('\theta')
    xlabel('x_{s,1}')
    ylabel('x_{s,2}')
end
view(-20,5);
%set(ha(1),'ZDir','reverse')
title('example optimizer trajectories')
ylim([-5.2,4])
grid on
set(gcf,'renderer','opengl'); 
%set(ha(1),'Ytick',[0,5]);

%%
[J,ind]=sort(parameters_EM.MS.logPost,'descend');
subplot(ha(2))
plot(-J,'-o')
ylim([-0.5,2])
xlabel('optimizer runs')
ylabel('objective function value')
title('convergence')

hlf=legend(ha(1),hl,'steady state','limit cycles','','','','example','trajectories','','','','','');
    set(hlf,'box','off','Position',[0.65, 0.2, 0.2, 0.1]);

feval('print', '-dpdf','-r300','FigureHopf.pdf');