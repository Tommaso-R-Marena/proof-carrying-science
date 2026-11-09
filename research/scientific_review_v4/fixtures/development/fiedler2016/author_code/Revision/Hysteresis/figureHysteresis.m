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

% subfigure numbering
text(.01,0.98,'A','FontName',setLay.lab.font,'FontSize',setLay.lab.size,'FontWeight',setLay.lab.weight);
text(.01,0.48,'B','FontName',setLay.lab.font,'FontSize',setLay.lab.size,'FontWeight',setLay.lab.weight);

ha(1) = axes('Position', [0.06, 0.58, 0.44, 0.38]);
ha(2) = axes('Position', [0.74, 0.58, 0.22, 0.38]);
ha(3) = axes('Position', [0.06, 0.07, 0.44, 0.38]);
ha(4) = axes('Position', [0.74, 0.07, 0.22, 0.38]);
%%

cur_dir = strrep(which('figureHysteresis'),'figureHysteresis.m','');
eval(['cd ' cur_dir]);

% load data
load('limitset.mat')
load('MS100_hysteresis.mat')

%%
indStart = [5,32,36,43,51];
Colvec = jet(7);
Colvec = max(Colvec-0.2,0);

subplot(ha(1))
hold on

lh(1)=plot(theta_eq(1:5885),x_eq(1:5885),'k','Linewidth',2.5);
lh(2)=plot(theta_eq(5885:6695),x_eq(5885:6695),'--k','Linewidth',2.5);
plot(theta_eq(6695:end),x_eq(6695:end),'k','Linewidth',2.5)

for i=1:length(indStart)
    plotIndex=indStart(i);
    lh(3+i)=plot(parameters_EM.MS.par_evol{plotIndex}(:,1),parameters_EM.MS.par_evol{plotIndex}(:,2),'Color',Colvec(i+2,:));
    hold on
    plot(parameters_EM.MS.par0(1,plotIndex),parameters_EM.MS.par0(2,plotIndex),'o','Color',Colvec(i+2,:))
    plot(parameters_EM.MS.par(1,plotIndex),parameters_EM.MS.par(2,plotIndex),'*','Color',Colvec(i+2,:))
end
lh(3)=plot(theta_opt,d_opt,'*r','Markersize',5);
xlim([-0.5 1.5])
xlabel('\theta')
ylabel('x_s')
title('example optimizer trajectories')

%%
[J,~]=sort(parameters_EM.MS.logPost,'descend');
subplot(ha(2))
plot(-J,'-o')
ylim([-0.5,2])
xlabel('optimizer runs')
ylabel('objective function value')
title('convergence')

%%
subplot(ha(3))
hold on
plot(theta_eq(1:5885),x_eq(1:5885),'k','Linewidth',2.5)
plot(theta_eq(5885:6695),x_eq(5885:6695),'--k','Linewidth',2.5)
plot(theta_eq(6695:end),x_eq(6695:end),'k','Linewidth',2.5)
for i=1:length(indStart)
    plotIndex=indStart(i);
    hl2(1+i)=plot(parameters_FMs.MS.evol{plotIndex}(1,:),parameters_FMs.MS.evol{plotIndex}(2,:),'Color',Colvec(i+2,:));
    hold on
    plot(parameters_FMs.MS.par0(1,plotIndex),parameters_FMs.MS.par0(2,plotIndex),'o','Color',Colvec(i+2,:))
    plot(parameters_FMs.MS.par(1,plotIndex),parameters_FMs.MS.par(2,plotIndex),'*','Color',Colvec(i+2,:))
end
hl2(1)=plot(theta_opt,d_opt,'*r','Markersize',5);
xlim([-0.5 1.5])
xlabel('\theta')
ylabel('x_s')
title('example optimizer trajectories')

%%
[J,~]=sort(parameters_FMs.MS.logPost,'descend');
subplot(ha(4))
plot(-J,'-o')
ylim([-0.5,2])
xlabel('optimizer runs')
ylabel('objective function value')
title('convergence')

lhf = legend(ha(1),lh,'bifurcation','diagram','optimum','','example','trajectories','','');
set(lhf,'box','off','Position',[0.57 0.45 0.07 0.12])

feval('print', '-dpdf','-r300','FigureHysteresis.pdf');