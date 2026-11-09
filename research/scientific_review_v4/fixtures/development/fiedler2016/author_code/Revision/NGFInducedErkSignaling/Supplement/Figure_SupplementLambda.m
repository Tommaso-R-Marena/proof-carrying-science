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

%% Figure 5.2: Pom1p data
clc; close all; clearvars -except 'setLay'

% print
printBoolean = true;

% set figure properties
close all;
fig = figure(1);
f_width = 0.9*setLay.txt.width;
f_height = 0.75*setLay.txt.height;
set(fig,'Color',[1 1 1],...
        'Units','centimeters',...
        'Position', [0,0,f_width,f_height],...
        'PaperSize',[f_width f_height],...
        'PaperPosition', [0,0,f_width f_height],...
        'PaperSize', [f_width f_height])

% create axis
h = axes('Position',[0 0 1 1],'Visible','off');

%%
ha(1) = axes('Position', [0.1, 0.4, 0.37, 0.56]);
ha(2) = axes('Position', [0.1, 0.12, 0.37, 0.25]);
ha(3) = axes('Position', [0.59, 0.4, 0.37, 0.56]);
ha(4) = axes('Position', [0.59, 0.12, 0.37, 0.25]);

%%
colvec = colormap(jet(10));

cur_dir = strrep(which('Figure_SupplementLambda'),'Figure_SupplementLambda.m','');
eval(['cd ' cur_dir]);

% load data
load('../Results/ResultManuscriptMS100_FUa.mat')
load('MS100lambdaMoreSteps.mat')

sortConvergedLambda
%% boxplot SD

subplot(ha(1))
hold on;
    boxplot(log10([parameters_SD{1}.MS.t_cpu,parameters_SD{2}.MS.t_cpu,parameters_SD{3}.MS.t_cpu,...
        parameters_SD{4}.MS.t_cpu,parameters_SD{5}.MS.t_cpu,parameters_SD{6}.MS.t_cpu,...
        parameters_SD{7}.MS.t_cpu,parameters_SD{8}.MS.t_cpu,parameters_SD{9}.MS.t_cpu,...
        parameters_SD{10}.MS.t_cpu]),...
        'colors',max(colvec(1:10,:)-0.25,0),'symbol','+','outliersize',4);
    
    ylim(log10([0.6 40]))
    
    set(ha(1),'XTickLabel',{''},...
    'YTick',log10([0.01:0.01:0.09,0.1:0.1:0.9,1:9,10:10:90]),...
       'YTickLabel',{'10^{-2}','','','','','','','','','10^{-1}',...
       '','','','','','','','','10^0','','','','','','','','','10^1','','','','','','','',''},...
        'Fontsize',8,'TickLabelInterpreter','tex')
    ylabel('computation time for individual start [s]','FontName',setLay.ax.font,'FontSize',setLay.ax.size)
    title('gradient descent','FontName',setLay.tit.font,'Fontsize',setLay.tit.size)
    set(findobj(gcf,'LineStyle','--'),'LineStyle','-')
    
%% computation time per converged start SD

subplot(ha(2))    
    for k=1:10
        plot(k,t_effectiveSD(k),'o','Color',max(colvec(k,:)-0.25,0))
        hold on
    end
    
    xlim([0.9 10.1])
     ylim([5 120])
    
    set(ha(2),'XTick',(1:10),'XTickLabel',{num2str(round(lambda_try(1),2)),...
        num2str(round(lambda_try(2),2)),num2str(round(lambda_try(3),2)),num2str(round(lambda_try(4),2)),...
        num2str(round(lambda_try(5),2)),num2str(round(lambda_try(6),2)),num2str(round(lambda_try(7),2)),...
        num2str(round(lambda_try(8),2)),num2str(round(lambda_try(9),2)),num2str(round(lambda_try(10),2))},...
    'XTickLabelRotation',45,'Fontsize',8,'yscale','log')
    
    xlabel('retraction factor \lambda','FontName',setLay.ax.font,'Fontsize',setLay.ax.size)
    ylabel({'average computation time'; 'per converged start [s]'},'FontName',setLay.ax.font,'Fontsize',setLay.ax.size)

%% boxplot NM

subplot(ha(3))
hold on;
    boxplot(log10([parameters_NM{1}.MS.t_cpu,parameters_NM{2}.MS.t_cpu,parameters_NM{3}.MS.t_cpu,...
        parameters_NM{4}.MS.t_cpu,parameters_NM{5}.MS.t_cpu,parameters_NM{6}.MS.t_cpu,...
        parameters_NM{7}.MS.t_cpu,parameters_NM{8}.MS.t_cpu,parameters_NM{9}.MS.t_cpu,...
        parameters_NM{10}.MS.t_cpu]),...
        'colors',max(colvec(1:10,:)-0.25,0),'symbol','+','outliersize',4); %'orientation','horizontal',
    
    ylim(log10([0.6 40]))
    
    set(ha(3),'XTickLabel',{''},'YTick',log10([0.01:0.01:0.09,0.1:0.1:0.9,1:9,10:10:90]),...
        'YTickLabel',{'10^{-2}','','','','','','','','','10^{-1}',...
        '','','','','','','','','10^0','','','','','','','','','10^1','','','','','','','',''},'Fontsize',8,'TickLabelInterpreter','tex') % ,'yscale','log' 
    
    ylabel('computation time for individual start [s]','FontName',setLay.ax.font,'FontSize',setLay.ax.size)
    title('newton-type method','FontName',setLay.tit.font,'Fontsize',setLay.tit.size)
    set(findobj(gcf,'LineStyle','--'),'LineStyle','-')

%% computation time per converged start NM

subplot(ha(4))
    for k=1:10
        plot(k,t_effectiveNM(k),'o','Color',max(colvec(k,:)-0.25,0))
        hold on
    end
    
    xlim([0.9 10.1])
    ylim([5 120])
    set(ha(4),'XTick',(1:10),'XTickLabel',{num2str(round(lambda_try(1),2)),...
        num2str(round(lambda_try(2),2)), num2str(round(lambda_try(3),2)),num2str(round(lambda_try(4),2)),...
        num2str(round(lambda_try(5),2)),num2str(round(lambda_try(6),2)),num2str(round(lambda_try(7),2)),...
        num2str(round(lambda_try(8),2)),num2str(round(lambda_try(9),2)),num2str(round(lambda_try(10),2))},...
       'XTickLabelRotation',45,'yscale','log','Fontsize',8)

    ylabel({'average computation time'; 'per converged start [s]'},'FontName',setLay.ax.font,'Fontsize',setLay.ax.size)
    xlabel('retraction factor \lambda','FontName',setLay.ax.font,'Fontsize',setLay.ax.size)

% save PDF of Figure
feval('print', '-dpdf','-r300','Figure_LambdaSupplement.pdf');
