import random 

# Number of individuals in each generation 
POPULATION_SIZE = 1000

# Valid genes 
GENES = '''abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOP 
QRSTUVWXYZ 1234567890, .-;:_!"#%&*<>^/()=?@${[]}'''

# Target string to be generated 
TARGET = "Testing Phrase Yes this is a testing pdfsdogiosgpeiowr84324"

class Individual(object): 
    ''' 
    Class representing individual in population 
    '''
    def __init__(self, chromosome): 
        self.chromosome = chromosome  
        self.fitness = self.cal_fitness() 

    @classmethod
    def weighted_random_choice(cls, target_gene):
        ''' 
        Select a gene with a higher probability if it is closer to the target gene 
        '''
        global GENES
        weights = []
        for gene in GENES:
            # Calculate the weight based on the difference from the target gene
            weight = 1.0 / (1 + abs(ord(gene) - ord(target_gene)))
            weights.append(weight)
        total_weight = sum(weights)
        probabilities = [weight / total_weight for weight in weights]
        return random.choices(GENES, probabilities)[0]

    @classmethod
    def mutated_genes(cls, target_gene): 
        ''' 
        create random genes for mutation 
        '''
        return cls.weighted_random_choice(target_gene)

    @classmethod
    def create_gnome(cls): 
        ''' 
        create chromosome or string of genes 
        '''
        global TARGET 
        gnome_len = len(TARGET) 
        return [cls.mutated_genes(TARGET[i]) for i in range(gnome_len)] 

    def mate(self, par2, mutation_rate): 
        ''' 
        Perform mating and produce new offspring 
        '''

        # chromosome for offspring 
        child_chromosome = [] 
        for gp1, gp2, target_gene in zip(self.chromosome, par2.chromosome, TARGET):     

            # random probability 
            prob = random.random() 

            # if prob is less than 0.45, insert gene 
            # from parent 1 
            if prob < 0.45:
                child_chromosome.append(gp1) 

            # if prob is between 0.45 and 0.90, insert 
            # gene from parent 2 
            elif prob < 0.90: 
                child_chromosome.append(gp2) 

            # otherwise insert guided mutation gene 
            # for maintaining diversity 
            else: 
                if random.random() < mutation_rate:
                    child_chromosome.append(self.mutated_genes(target_gene))
                else:
                    child_chromosome.append(gp1 if random.random() < 0.5 else gp2)

        # create new Individual(offspring) using 
        # generated chromosome for offspring 
        return Individual(child_chromosome) 

    def cal_fitness(self): 
        ''' 
        Calculate fitness score, it is the number of 
        characters in string which differ from target 
        string. 
        '''
        global TARGET 
        fitness = 0
        for gs, gt in zip(self.chromosome, TARGET): 
            if gs != gt: fitness += 1
        
        return fitness 

# Driver code 
def main(): 
    global POPULATION_SIZE 

    # current generation 
    generation = 1

    found = False
    population = [] 

    # create initial population 
    for _ in range(POPULATION_SIZE): 
        gnome = Individual.create_gnome() 
        population.append(Individual(gnome)) 

    while not found: 

        # sort the population in increasing order of fitness score 
        population = sorted(population, key = lambda x:x.fitness) 

        # if the individual having lowest fitness score ie.  
        # 0 then we know that we have reached to the target 
        # and break the loop 
        if population[0].fitness <= 0: 
            found = True
            break

        # Calculate dynamic mutation rate
        best_fitness = population[0].fitness
        mutation_rate = 0.1 + (0.9 * (1 - (best_fitness / len(TARGET))))

        # Otherwise generate new offsprings for new generation 
        new_generation = [] 

        # Perform Elitism, that mean 10% of fittest population 
        # goes to the next generation 
        s = int((10*POPULATION_SIZE)/100) 
        new_generation.extend(population[:s]) 

        # From 50% of fittest population, Individuals  
        # will mate to produce offspring 
        s = int((90*POPULATION_SIZE)/100) 
        for _ in range(s): 
            parent1 = random.choice(population[:75]) 
            parent2 = random.choice(population[:75]) 
            child = parent1.mate(parent2, mutation_rate) 
            new_generation.append(child) 

        population = new_generation 

        print("Generation: {}\tString: {}\tFitness: {}\tMutation Rate: {:.2f}".
              format(generation, 
              "".join(population[0].chromosome), 
              population[0].fitness,
              mutation_rate)) 

        generation += 1

    print("Generation: {}\tString: {}\tFitness: {}".
          format(generation, 
          "".join(population[0].chromosome), 
          population[0].fitness)) 

if __name__ == '__main__': 
    main()