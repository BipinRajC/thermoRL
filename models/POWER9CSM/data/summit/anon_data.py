import csv
import numpy as np
import copy
import random
import matplotlib.pyplot as plt


class csv_data:

    def __init__(self, filename):

        self.filename = filename

        self.headers = []*0

        self.data = [[]*0 for i in range(0)]


        self.load_data()





    def load_data(self):

        with open(self.filename, 'r') as file:

            header_check = False

            csv_reader = csv.reader(file)
            for row in csv_reader:
                if row[0] != '':

                    if header_check:
                        if len(self.data) != len(row):
                            self.data = [[]*0 for i in range(len(row))]
                
                        for i in range(len(row)):
                            self.data[i].append(float(row[i].replace("ï»¿", "")))
                    
                    else:
                        header_check = True
                        for i in range(len(row)):
                            self.headers.append(row[i].replace("ï»¿", ""))
                    

                else:
                    break







class data_center_data:

    def __init__(self, cooling_filename, cab_filenames):

        self.cooling_data = csv_data(cooling_filename)

        self.cabinet_data = []*0

        for i in range(len(cab_filenames)):

            self.cabinet_data.append(csv_data(cab_filenames[i]))



        

        #Anonymous Data Params
        self.center_shift = 2   #% of average for window of randomness

        self.walk_step = 10      #% of range for random fuctuations







    

    def gen_anon_DC(self, num_figs=None):



        anon_DC = copy.deepcopy(self)

        fig_count = 0

        for i in range(1,len(self.cooling_data.data)):

            ave = np.average(self.cooling_data.data[i])

            min = np.min(self.cooling_data.data[i])

            max = np.max(self.cooling_data.data[i])


            span = max-min

            step = span*(self.walk_step/100)


            center = ave + (-1 + 2*random.random())*(self.center_shift/100)*ave

            cur_val = random.uniform(center - span/2, center + span/2)

            



            for j in range(len(self.cooling_data.data[i])):

                anon_DC.cooling_data.data[i][j] = cur_val + random.uniform(-1,1)* step

                if anon_DC.cooling_data.data[i][j] < 0:

                    anon_DC.cooling_data.data[i][j] = 0

            


            if num_figs != None and fig_count < num_figs:

                fig_count += 1

                plt.figure(fig_count)

                plt.plot(self.cooling_data.data[0], self.cooling_data.data[i])

                plt.plot(anon_DC.cooling_data.data[0], anon_DC.cooling_data.data[i])






        for i in range(len(self.cabinet_data)):

            for j in range(1,len(self.cabinet_data[i].data)):

                ave = np.average(self.cabinet_data[i].data[j])

                min = np.min(self.cabinet_data[i].data[j])

                max = np.max(self.cabinet_data[i].data[j])

                span = max-min

                step = span*(self.walk_step/100)


                center = ave + (-1 + 2*random.random())*(self.center_shift/100)*ave

                cur_val = random.uniform(center - span/2, center + span/2)

                

                for k in range(len(self.cabinet_data[i].data[j])):

                    anon_DC.cabinet_data[i].data[j][k] = cur_val + random.uniform(-1,1)* step

                    if anon_DC.cabinet_data[i].data[j][k] < 0:

                        anon_DC.cabinet_data[i].data[j][k] = 0

            


                if num_figs != None and fig_count < num_figs:

                    fig_count += 1

                    plt.figure(fig_count)

                    plt.plot(self.cabinet_data[i].data[0], self.cabinet_data[i].data[j])

                    plt.plot(anon_DC.cabinet_data[i].data[0], anon_DC.cabinet_data[i].data[j])
        


        plt.show()

        return anon_DC










    def save_CSVs(self, folder="Anon_Data"):

        for i in range(len(self.cooling_data.data[0])+1):

            if i == 0:

                data_out = []

                cur_row = []

                for j in range(len(self.cooling_data.headers)):

                    cur_row.append(self.cooling_data.headers[j])
                
                data_out.append(cur_row)

            else:

                cur_row = []

                for j in range(len(self.cooling_data.data)):

                    cur_row.append(str(round(self.cooling_data.data[j][i-1],3)))
                
                data_out.append(cur_row)
        

        with open(folder+'/Cooling_Data.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(data_out)


        


        for i in range(len(self.cabinet_data)):

            for j in range(len(self.cabinet_data[i].data[0])+1):

                if j == 0:

                    data_out = []

                    cur_row = []

                    for k in range(len(self.cabinet_data[i].headers)):

                        cur_row.append(self.cabinet_data[i].headers[k])
                    
                    data_out.append(cur_row)

                else:

                    cur_row = []

                    for k in range(len(self.cabinet_data[i].data)):

                        cur_row.append(str(round(self.cabinet_data[i].data[k][j-1],3)))
                    
                    data_out.append(cur_row)
            

            with open(folder+'/Cabinet_Data/cabinet'+str(i)+'.csv', 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerows(data_out)


















cooling_filename = "Summit_Thermo_Data_2020-1-20.csv"

num_cabs = 257
cab_filenames = []*0
for i in range(num_cabs):
    cab_filenames.append("cabinet_data_20200120/cab_"+str(i+1)+"_timeseries.csv")


DC = data_center_data(cooling_filename, cab_filenames)

ADC = DC.gen_anon_DC(8)

ADC.save_CSVs()

